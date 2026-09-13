import uvicorn
import json
import pandas as pd
import numpy as np
import faiss
import cv2
import re
import torch
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer, CrossEncoder
import easyocr
from collections import Counter
from rapidfuzz import process, fuzz
from ctransformers import AutoModelForCausalLM

# ==========================================
# 1. CONFIGURATION
# ==========================================
app = FastAPI(title="Anesthesia Guard AI", version="Final")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RAGRequest(BaseModel):
    query: str

# --- MODÈLE DE DONNÉES DU FORMULAIRE PATIENT ---
class PatientProfile(BaseModel):
    age: int = 0             # Valeur par défaut 0 pour éviter l'erreur 422
    weight: int = 0          # Poids en kg
    height: int = 0          # Taille en cm
    
    # Cases à cocher (Booleans)
    is_smoker: bool = False
    is_alcoholic: bool = False
    has_diabetes: bool = False
    has_hypertension: bool = False
    has_respiratory_issues: bool = False
    
    # Champs textes
    recent_events: str = "Aucun" 
    detected_medications: list[str] = []

asa_definitions_list = []

print("\n\n⚡ *** DÉMARRAGE MODE CORRIGÉ (ANTI-HALLUCINATION) *** ⚡")

# 0. HARDWARE
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"⚙️ Matériel : {device.upper()}")

# 1. MODÈLES
print("1️⃣ Chargement Embeddings & OCR...")
embedder = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', device=device)
reranker = CrossEncoder('BAAI/bge-reranker-base', device=device)
reader = easyocr.Reader(['fr', 'en'], gpu=(device == "cuda"))

# 2. CSV (OCR)
try:
    df_drugs = pd.read_csv("medicaments_frances_approx_poso_full.csv", sep=';', encoding='utf-8-sig')
    df_drugs['drug_name'] = df_drugs['drug_name'].astype(str).str.strip()
    df_drugs['sub_category'] = df_drugs['sub_category'].astype(str).str.strip()
    df_drugs['drug_name_norm'] = df_drugs['drug_name'].str.upper()
    drug_names = df_drugs['drug_name'].tolist()
    drug_names_norm = df_drugs['drug_name_norm'].tolist()
    print("✅ CSV OK.")
except:
    df_drugs = pd.DataFrame()
    drug_names = []
    drug_names_norm = []

# 3. JSON (RAG) - TEXTIFY AMÉLIORÉ
try:
    with open("data_anesthesie.json", 'r', encoding='utf-8') as f:
        rag_data = json.load(f)

    def textify(entry):
        # ON MET LE NOM DU MÉDICAMENT EN MAJUSCULE AU DÉBUT
        prefix = f"PROTOCOLE POUR : {entry.get('medication', 'INCONNU').upper()}."
        
        if "decision_J_0_morning" in entry:
            j2 = "MAINTENIR" if entry.get("decision_J_minus_2") == "Oui" else "ARRÊTER"
            j1 = "MAINTENIR" if entry.get("decision_J_minus_1") == "Oui" else "ARRÊTER"
            j0 = "MAINTENIR" if entry.get("decision_J_0_morning") == "Oui" else "ARRÊTER"
            
            return (
                f"{prefix} Catégorie: {entry.get('category')}. "
                f"J-2: {j2}. J-1: {j1}. "
                f"MATIN OPÉRATION (J0): {j0}. "
                f"Risque arrêt: {entry.get('risk_if_stopped')}. "
                f"Précautions: {entry.get('precautions')}"
            )
        elif "score" in entry:
            # ON INCLUT EXPLICITEMENT LES EXEMPLES DANS LE TEXTE
            # C'est ça qui va permettre à l'IA de voir "Obésité Morbide" dans ASA III
            desc = (f"SCORE {entry.get('score')} : {entry.get('description')}. "f"LISTE DES CAS (EXEMPLES) : {entry.get('exemples')}")
            asa_definitions_list.append(desc)
            return desc

        elif "medication" in entry:
            return f"{prefix} Consigne: {entry.get('instruction') or entry.get('instruction_arret')}."
        
        return str(entry)

    rag_docs = [textify(e) for e in rag_data]
    rag_vectors = embedder.encode(rag_docs)
    rag_index = faiss.IndexFlatL2(rag_vectors.shape[1])
    rag_index.add(rag_vectors)
    print("✅ JSON OK (Indexation Renforcée).")

except Exception as e:
    print(f"⚠️ Erreur JSON: {e}")
    rag_docs = []
    rag_index = None

# 4. MISTRAL
print("⏳ Chargement Mistral...")
model_id = "TheBloke/Mistral-7B-Instruct-v0.2-GGUF"
try:
    llm = AutoModelForCausalLM.from_pretrained(model_id, model_file="mistral-7b-instruct-v0.2.Q4_K_M.gguf", model_type="mistral", context_length=2048, gpu_layers=0)
    print("✅ Mistral OK.")
except:
    llm = None


# ==========================================
# 3. ENDPOINTS
# ==========================================

@app.post("/ocr/scan")
async def scan_drug(file: UploadFile = File(...)):
    print(f"📸 Scan Image: {file.filename}")
    
    # 0. Lecture de l'image (OpenCV)
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # 1. OCR EasyOCR
    result = reader.readtext(img)
    full_ocr = " ".join([t[1].upper() for t in result if len(t[1]) > 2])
    
    # Extraction des mots clés (Majuscules, 3 à 15 lettres)
    words = re.findall(r'\b[A-Z]{3,15}\b', full_ocr)

    print(f"🔍 Mots détectés: {words}")

    if not words:
        return {"drugName": None, "confidence": 0.0, "subCategory": "Inconnu"}

    # 2. LOGIQUE DE VOTE (Exact + Fuzzy)
    votes = Counter()
    for word in words:
        # A. Match Exact
        if word in drug_names_norm:
            idx = drug_names_norm.index(word)
            votes[drug_names[idx]] += 100
        
        # B. Fuzzy Match (ex: FLUDEXLP -> FLUDEX)
        fuzzy_matches = process.extract(word, drug_names_norm, limit=2, score_cutoff=80)
        
        for match in fuzzy_matches:
            # Gestion compatibilité versions rapidfuzz
            if len(match) >= 3:
                drug_found = drug_names[match[2]]
                votes[drug_found] += (match[1] / 100) * 15

    if not votes:
         return {"drugName": None, "confidence": 0.0, "subCategory": "Inconnu"}

    # 3. Sélection du gagnant
    winner = votes.most_common(1)[0][0]
    confidence = votes[winner] / sum(votes.values())

    # 4. Récupération de la Sub-catégorie depuis le DataFrame
    try:
        matching_rows = df_drugs[df_drugs['drug_name'] == winner]
        if not matching_rows.empty:
            sub_cat = matching_rows.iloc[0]['sub_category']
        else:
            sub_cat = "Inconnu"
    except:
        sub_cat = "Inconnu"

    print(f"🏆 Gagnant: {winner} ({confidence:.2%})")
    
    return {
        "drugName": winner, 
        "subCategory": sub_cat, 
        "confidence": confidence
    }


@app.post("/rag/protocol")
async def get_protocol(req: RAGRequest):
    print(f"\n❓ Question reçue : {req.query}")
    query_upper = req.query.upper()
    best_doc = ""

    # --- CAS SPÉCIAL : CALCUL DE SCORE ASA ---
    # Si la question parle de "ASA" ou "SCORE", on donne TOUTES les définitions à l'IA
# --- CAS SPÉCIAL : CALCUL DE SCORE ASA (CHAT) ---
    if "ASA" in query_upper or "SCORE" in query_upper or "OBÉSITÉ" in query_upper or "DIABÈTE" in query_upper:
        print("🎯 MODE DIAGNOSTIC : SCORE ASA DETECTÉ")
        # On force l'IA à voir TOUTES les définitions ASA pour comparer
        all_asa_docs = [d for d in rag_docs if "SCORE ASA" in d]
        best_doc = "\n---\n".join(all_asa_docs)
    
    # --- CAS STANDARD : MÉDICAMENTS ---
    else:
        # 1. Détection par nom de médicament (Fuzzy Match dans la base JSON)
        all_meds_in_db = []
        for doc in rag_docs:
            try:
                if "PROTOCOLE POUR :" in doc:
                    name = doc.split("PROTOCOLE POUR : ")[1].split(".")[0]
                    all_meds_in_db.append(name)
            except: pass
        
        best_match_name = None
        best_match_score = 0

        # Recherche floue (RapidFuzz) pour trouver le médicament dans la question
        for med in all_meds_in_db:
            if "ASA" in med: continue # On ignore les ASA ici
            score = fuzz.partial_ratio(med, query_upper)
            if score > 85 and score > best_match_score:
                best_match_score = score
                best_match_name = med

        if best_match_name:
            print(f"🎯 MÉDICAMENT IDENTIFIÉ DANS LA QUESTION : {best_match_name}")
            best_doc = next((d for d in rag_docs if f"PROTOCOLE POUR : {best_match_name}" in d), rag_docs[0])
        else:
            print("⚠️ Recherche Vectorielle (FAISS)...")
            q_vec = embedder.encode([req.query])
            D, I = rag_index.search(q_vec, k=5)
            candidates = [rag_docs[i] for i in I[0]]
            pairs = [[req.query, doc] for doc in candidates]
            scores = reranker.predict(pairs)
            best_doc = candidates[scores.argmax()]

    print(f"📄 CONTEXTE ENVOYÉ À L'IA : {best_doc[:100]}...") # Juste le début pour debug

    # 3. GENERATION
    if llm is None: return {"protocol": best_doc, "riskLevel": "Unknown"}

    prompt = (
        f"[INST] <<SYS>>\n"
        f"Tu es un assistant anesthésiste expert. Réponds en FRANÇAIS uniquement.\n"
        f"Si on te demande si on doit arrêter un médicament, réponds clairement par 'ARRÊTER' ou 'MAINTENIR'.\n"
        f" Sois DIRECT, BREF et IMPÉRATIF.\n"
        f"<</SYS>>\n\n"
        f"CONTEXTE MÉDICAL :\n{best_doc}\n\n"
        f"QUESTION : {req.query}\n\n"
        f"RÉPONSE (En français, justifiée) : [/INST]"
    )
    
    raw_answer = llm(prompt, max_new_tokens=250, temperature=0.1)
    natural_answer = raw_answer.strip()
    
    is_high_risk = "ARRÊTER" in natural_answer.upper() or "NE DOIT PAS" in best_doc.upper()
    risk = "High" if is_high_risk else "Low"

    return {"protocol": natural_answer, "riskLevel": risk}


# =========================================================
# 4. ENDPOINT CALCUL ASA (FORMULAIRE + MEDS)
# =========================================================
@app.post("/asa/evaluate")
async def evaluate_asa_score(profile: PatientProfile):
    """
    Reçoit le formulaire (Cases à cocher Oui/Non + Age + Meds).
    Calcule l'IMC.
    Envoie le tout au LLM pour décision ASA.
    """
    print(f"\n📊 CALCUL ASA FORMULAIRE : {profile}")

    # 1. Calcul automatique du BMI (IMC) si taille et poids sont là
    bmi_info = "Non calculable"
    if profile.height > 0 and profile.weight > 0:
        height_m = profile.height / 100
        bmi = profile.weight / (height_m * height_m)
        bmi_info = f"{bmi:.1f}"
        if bmi > 40: bmi_info += " (OBÉSITÉ MORBIDE)"
        elif bmi > 30: bmi_info += " (OBÉSITÉ)"

    # 2. Construction du "Dossier Patient" lisible pour l'IA
    # On transforme les Booleans (True/False) en texte (OUI/NON)
    resume = f"- Âge : {profile.age} ans\n"
    resume += f"- BMI (IMC) : {bmi_info}\n"
    resume += f"- Fumeur : {'OUI' if profile.is_smoker else 'NON'}\n"
    resume += f"- Alcool : {'OUI' if profile.is_alcoholic else 'NON'}\n"
    resume += f"- Diabète : {'OUI' if profile.has_diabetes else 'NON'}\n"
    resume += f"- Hypertension (HTA) : {'OUI' if profile.has_hypertension else 'NON'}\n"
    resume += f"- Problèmes Respiratoires : {'OUI' if profile.has_respiratory_issues else 'NON'}\n"
    resume += f"- Événements Récents (AVC/Infarctus) : {profile.recent_events}\n"
    resume += f"- Médicaments détectés : {', '.join(profile.detected_medications)}\n"

    # 3. Récupération des définitions ASA (depuis le JSON chargé)
    if not asa_definitions_list:
        definitions_text = "\n".join([d for d in rag_docs if "SCORE ASA" in d])
    else:
        definitions_text = "\n".join(asa_definitions_list)

    if not llm: return {"score": "Indéterminé", "raw_analysis": "LLM HS"}

    # 4. PROMPT STRICT
    prompt = (
        f"[INST] <<SYS>>\n"
        f"Tu es un médecin anesthésiste expert. Calcule le score ASA (I, II, III, IV, V, VI).\n"
        f"RÈGLES DE DÉCISION :\n"
        f"1. ASA I : Patient sain (Non fumeur, pas d'alcool, BMI < 30): Bonne santé, non fumeur, pas ou consommation minimale d’alcool\n"
        f"2. ASA II : Fumeur, Alcool social, Obésité (BMI<40), HTA/Diabète bien contrôlé.\n"
        f"3. ASA III : Obésité Morbide (BMI > 40), Diabète/HTA mal contrôlé, BPCO, Hépatite.\n"
        f"4. ASA IV : Infarctus ou AVC récent (< 3 mois), menace vitale constante.\n"
        f"5. La prise de médicaments confirme les pathologies (ex: Beta-bloquant = HTA).\n"
        f"<</SYS>>\n\n"
        f"DÉFINITIONS OFFICIELLES :\n{definitions_text}\n\n"
        f"DOSSIER PATIENT :\n{resume}\n\n"
        f"Quel est le score ASA ? Réponds au format JSON strict : {{ \"score\": \"ASA X\", \"justification\": \"Une phrase courte.\" }} [/INST]"
    )

    # Appel IA
    response = llm(prompt, max_new_tokens=250, temperature=0.1)
    print(f"🤖 Analyse ASA : {response}")

    # Extraction propre du score
    import re
    match = re.search(r"ASA [IV]+", response)
    score_final = match.group(0) if match else "ASA Indéterminé"

    return {"score": score_final, "raw_analysis": response}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8050)