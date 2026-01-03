// API Configuration for AnesthesiaGuard Backend
const API_BASE_URL = "http://localhost:8050";

export interface OcrScanResponse {
  drugName: string;
  subCategory: string;
  confidence?: number;
}

export interface ProtocolResponse {
  protocol: string;
  riskLevel: "STOP" | "CONTINUE";
}

export interface ASAEvaluateRequest {
  age: number;
  medications: string[];
}

export interface ASAEvaluateResponse {
  score: string;
  description: string;
}

export interface Patient {
  id: string;
  name: string;
  age: number;
  operationType: string;
  asaScore: string;
  medications: ScannedMedication[];
  createdAt: string;
}

export interface ScannedMedication {
  id: string;
  commercialName: string;
  genericName: string;
  instruction: string;
  riskLevel: "STOP" | "CONTINUE";
  confidence?: number;
  scannedAt: string;
}

// OCR Scan endpoint
export async function scanMedication(imageFile: File): Promise<OcrScanResponse> {
  const formData = new FormData();
  formData.append("image", imageFile);

  const response = await fetch(`${API_BASE_URL}/ocr/scan`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error("Failed to scan medication");
  }

  return response.json();
}

// Protocol/Chat endpoint
export async function getProtocol(query: string): Promise<ProtocolResponse> {
  const response = await fetch(`${API_BASE_URL}/rag/protocol`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ query }),
  });

  if (!response.ok) {
    throw new Error("Failed to get protocol");
  }

  return response.json();
}

// ASA Score evaluation
export async function evaluateASA(data: ASAEvaluateRequest): Promise<ASAEvaluateResponse> {
  const response = await fetch(`${API_BASE_URL}/asa/evaluate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error("Failed to evaluate ASA score");
  }

  return response.json();
}

// Mock data for demo (when backend is not available)
export const mockPatients: Patient[] = [
  {
    id: "1",
    name: "Jean Dupont",
    age: 65,
    operationType: "Arthroplastie du genou",
    asaScore: "ASA II",
    medications: [
      {
        id: "m1",
        commercialName: "Kardegic",
        genericName: "Aspirine",
        instruction: "Arrêter 5 jours avant l'intervention chirurgicale pour réduire le risque de saignement.",
        riskLevel: "STOP",
        scannedAt: new Date().toISOString(),
      },
      {
        id: "m2",
        commercialName: "Doliprane",
        genericName: "Paracétamol",
        instruction: "Peut être continué jusqu'au jour de l'opération. Pas de risque d'interaction avec l'anesthésie.",
        riskLevel: "CONTINUE",
        scannedAt: new Date().toISOString(),
      },
    ],
    createdAt: new Date().toISOString(),
  },
  {
    id: "2",
    name: "Marie Martin",
    age: 45,
    operationType: "Cholécystectomie",
    asaScore: "ASA I",
    medications: [
      {
        id: "m3",
        commercialName: "Levothyrox",
        genericName: "Lévothyroxine",
        instruction: "Continuer le traitement. Prendre le matin de l'intervention avec une gorgée d'eau.",
        riskLevel: "CONTINUE",
        scannedAt: new Date().toISOString(),
      },
    ],
    createdAt: new Date().toISOString(),
  },
  {
    id: "3",
    name: "Pierre Bernard",
    age: 72,
    operationType: "Prothèse de hanche",
    asaScore: "ASA III",
    medications: [
      {
        id: "m4",
        commercialName: "Previscan",
        genericName: "Fluindione",
        instruction: "ARRÊT OBLIGATOIRE 5 jours avant. Relais par HBPM à discuter avec l'anesthésiste.",
        riskLevel: "STOP",
        scannedAt: new Date().toISOString(),
      },
      {
        id: "m5",
        commercialName: "Amlor",
        genericName: "Amlodipine",
        instruction: "Continuer le traitement. Maintenir la pression artérielle stable.",
        riskLevel: "CONTINUE",
        scannedAt: new Date().toISOString(),
      },
      {
        id: "m6",
        commercialName: "Metformine",
        genericName: "Metformine",
        instruction: "Arrêter 48h avant l'intervention. Risque d'acidose lactique.",
        riskLevel: "STOP",
        scannedAt: new Date().toISOString(),
      },
    ],
    createdAt: new Date().toISOString(),
  },
];

// Mock API responses for demo
export function mockScanMedication(): Promise<OcrScanResponse> {
  return new Promise((resolve) => {
    setTimeout(() => {
      const drugs = [
        { drugName: "Kardegic", subCategory: "Aspirine", confidence: 0.95 },
        { drugName: "Doliprane", subCategory: "Paracétamol", confidence: 0.92 },
        { drugName: "Previscan", subCategory: "Fluindione", confidence: 0.88 },
        { drugName: "Levothyrox", subCategory: "Lévothyroxine", confidence: 0.91 },
      ];
      resolve(drugs[Math.floor(Math.random() * drugs.length)]);
    }, 1500);
  });
}

export function mockGetProtocol(genericName: string): Promise<ProtocolResponse> {
  return new Promise((resolve) => {
    setTimeout(() => {
      const protocols: Record<string, ProtocolResponse> = {
        Aspirine: {
          protocol: "Arrêter 5 jours avant l'intervention chirurgicale pour réduire le risque de saignement. En cas de stent coronaire récent, discuter avec le cardiologue de la balance bénéfice/risque.",
          riskLevel: "STOP",
        },
        Paracétamol: {
          protocol: "Peut être continué jusqu'au jour de l'opération. Pas de risque d'interaction avec l'anesthésie. Utile pour la gestion de la douleur postopératoire.",
          riskLevel: "CONTINUE",
        },
        Fluindione: {
          protocol: "ARRÊT OBLIGATOIRE 5 jours avant l'intervention. Un relais par héparine de bas poids moléculaire (HBPM) doit être discuté avec l'anesthésiste selon le risque thrombotique.",
          riskLevel: "STOP",
        },
        Lévothyroxine: {
          protocol: "Continuer le traitement habituel. Prendre le comprimé le matin de l'intervention avec une petite gorgée d'eau, au moins 2 heures avant l'anesthésie.",
          riskLevel: "CONTINUE",
        },
      };
      resolve(
        protocols[genericName] || {
          protocol: "Veuillez consulter votre anesthésiste pour des recommandations personnalisées concernant ce médicament.",
          riskLevel: "CONTINUE",
        }
      );
    }, 1000);
  });
}

export function mockEvaluateASA(): Promise<ASAEvaluateResponse> {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        score: "ASA II",
        description: "Patient avec une maladie systémique légère",
      });
    }, 500);
  });
}

// API object for easy access (uses mocks for now)
export const api = {
  scanDrug: mockScanMedication,
  getProtocol: mockGetProtocol,
  evaluateASA: mockEvaluateASA,
};
