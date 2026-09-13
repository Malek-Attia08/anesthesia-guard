import { motion, AnimatePresence } from "framer-motion";
import { useState, useRef } from "react";
import { Camera, Upload, Loader2, Pill, AlertCircle, CheckCircle, ScanLine, Brain, ShieldCheck, ListPlus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { api, ScannedMedication } from "@/lib/api";
import { usePatientStore } from "@/store/patientStore";

// --- COMPOSANT CARTE RÉSULTAT ---
function ResultCard({ medication, onDelete }: { medication: ScannedMedication, onDelete: () => void }) {
  const isStop = medication.riskLevel === "STOP";

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, x: -50, scale: 0.9 }}
      transition={{ type: "spring", stiffness: 400, damping: 25 }}
    >
      <Card className={`overflow-hidden border-l-4 ${isStop ? 'border-l-red-500 bg-red-50/50 dark:bg-red-950/20' : 'border-l-green-500 bg-green-50/50 dark:bg-green-950/20'}`}>
        {/* BANDEAU DE TITRE COLORÉ */}
        <div className={`px-4 py-2 flex items-center justify-between ${isStop ? 'bg-red-100 dark:bg-red-900/30' : 'bg-green-100 dark:bg-green-900/30'}`}>
          <div className="flex items-center gap-2">
            {isStop ? <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400" /> : <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400" />}
            <span className={`text-xs font-bold uppercase tracking-wider ${isStop ? 'text-red-700 dark:text-red-300' : 'text-green-700 dark:text-green-300'}`}>
              {isStop ? "ARRÊT REQUIS" : "AUTORISÉ"}
            </span>
          </div>
          <Button variant="ghost" size="icon" className="h-6 w-6 text-muted-foreground hover:text-red-500" onClick={onDelete}>
            <Trash2 className="w-3.5 h-3.5" />
          </Button>
        </div>
        
        <CardContent className="p-4 space-y-3">
          {/* Info Médicament */}
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${isStop ? 'bg-red-100 dark:bg-red-900/50' : 'bg-green-100 dark:bg-green-900/50'}`}>
                <Pill className={`w-5 h-5 ${isStop ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`} />
              </div>
              <div>
                <p className="font-semibold text-foreground">{medication.commercialName}</p>
                <p className="text-xs text-muted-foreground flex items-center gap-1">
                  <Brain className="w-3 h-3" /> 
                  {medication.genericName}
                </p>
              </div>
            </div>
            {medication.confidence && (
              <Badge variant="secondary" className="text-xs">
                IA: {Math.round(medication.confidence * 100)}%
              </Badge>
            )}
          </div>
          
          {/* Consigne IA */}
          <div className={`p-3 rounded-lg text-sm ${isStop ? 'bg-red-100/70 dark:bg-red-900/40 text-red-800 dark:text-red-200' : 'bg-green-100/70 dark:bg-green-900/40 text-green-800 dark:text-green-200'}`}>
            <p className="leading-relaxed">{medication.instruction}</p>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

// --- COMPOSANT PRINCIPAL ---
export function MedicationScanner() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [scannedList, setScannedList] = useState<ScannedMedication[]>([]);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { addMedication } = usePatientStore();

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault(); e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") setDragActive(true);
    else if (e.type === "dragleave") setDragActive(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault(); e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) handleFile(e.target.files[0]);
  };

  const handleFile = async (file: File) => {
    if (!file.type.startsWith("image/")) { 
      toast.error("Image requise."); 
      return; 
    }
    
    setIsProcessing(true);
    
    try {
      // 1. OCR
      const ocrResult = await api.scanDrug();
      if (!ocrResult.drugName || ocrResult.drugName === "Non reconnu") {
        toast.error("Médicament non reconnu.");
        setIsProcessing(false);
        return;
      }
      
      // 2. RAG (Protocole)
      const protocolResult = await api.getProtocol(ocrResult.subCategory);
      
      const medication: ScannedMedication = {
        id: Date.now().toString(),
        commercialName: ocrResult.drugName,
        genericName: ocrResult.subCategory,
        instruction: protocolResult.protocol,
        riskLevel: protocolResult.riskLevel, 
        confidence: ocrResult.confidence,
        scannedAt: new Date().toISOString(),
      };

      // 3. Ajout à la liste
      setScannedList(prev => [medication, ...prev]);
      addMedication(medication);
      toast.success(`${ocrResult.drugName} ajouté !`);

    } catch (error) {
      console.error(error); 
      toast.error("Erreur lors de l'analyse.");
    } finally {
      setIsProcessing(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const removeMedication = (id: string) => {
    setScannedList(prev => prev.filter(m => m.id !== id));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-primary to-primary/70 shadow-lg">
            <Pill className="w-6 h-6 text-primary-foreground" />
          </div>
          <h2 className="text-xl font-bold text-foreground">
            AnesthesiaGuard
          </h2>
        </div>
        <Badge variant="secondary" className="text-sm">
          {scannedList.length} scan{scannedList.length > 1 ? 's' : ''}
        </Badge>
      </div>

      <Card>
        <CardHeader className="text-center pb-4">
          <CardTitle className="text-lg">Analysez vos médicaments</CardTitle>
          <CardDescription>Scannez vos boîtes une par une pour construire votre dossier.</CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* === GAUCHE : SCANNER === */}
            <div className="lg:col-span-5 space-y-4">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                capture="environment"
                onChange={handleFileInput}
                className="hidden"
              />
              
              <div
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => !isProcessing && fileInputRef.current?.click()}
                className={`
                  relative cursor-pointer rounded-2xl border-2 border-dashed p-8
                  transition-all duration-300 min-h-[200px] flex items-center justify-center
                  ${dragActive ? 'border-primary bg-primary/5 scale-[1.02]' : 'border-muted-foreground/30 hover:border-primary/50 hover:bg-muted/30'}
                  ${isProcessing ? 'pointer-events-none' : ''}
                `}
              >
                <AnimatePresence mode="wait">
                  {isProcessing ? (
                    <motion.div
                      key="processing"
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.8 }}
                      className="text-center"
                    >
                      <div className="relative mx-auto w-16 h-16 mb-4">
                        <div className="absolute inset-0 rounded-full border-4 border-primary/20" />
                        <div className="absolute inset-0 rounded-full border-4 border-primary border-t-transparent animate-spin" />
                      </div>
                      <p className="font-semibold text-foreground">Analyse IA...</p>
                      <p className="text-sm text-muted-foreground">Identification et vérification du protocole</p>
                    </motion.div>
                  ) : (
                    <motion.div
                      key="idle"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="text-center"
                    >
                      <div className="relative mx-auto w-16 h-16 mb-4">
                        <div className="absolute inset-0 rounded-full bg-primary/10 animate-pulse" />
                        <div className="absolute inset-0 flex items-center justify-center">
                          <Camera className="w-7 h-7 text-primary" />
                        </div>
                        <div className="absolute -top-1 -right-1 p-1.5 rounded-full bg-card border shadow-sm">
                          <Upload className="w-3 h-3 text-muted-foreground" />
                        </div>
                      </div>
                      <div>
                        <p className="font-semibold text-foreground">Scanner</p>
                        <p className="text-sm text-muted-foreground">Cliquez ou glissez une photo ici</p>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              <div className="flex justify-center gap-3 flex-wrap">
                {[
                  { icon: ScanLine, text: "OCR Rapide", color: "text-blue-500" },
                  { icon: Brain, text: "IA Médicale", color: "text-purple-500" },
                  { icon: ShieldCheck, text: "Sécurisé", color: "text-green-500" }
                ].map((badge, i) => (
                  <Badge key={i} variant="outline" className="gap-1.5 py-1 px-2.5">
                    <badge.icon className={`w-3.5 h-3.5 ${badge.color}`} />
                    {badge.text}
                  </Badge>
                ))}
              </div>
            </div>

            {/* === DROITE : LISTE DES RÉSULTATS === */}
            <div className="lg:col-span-7">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-muted-foreground flex items-center gap-2">
                  <ListPlus className="w-4 h-4" />
                  Votre liste de médicaments
                </h3>
                {scannedList.length > 0 && (
                  <Button variant="ghost" size="sm" onClick={() => setScannedList([])} className="text-red-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950">
                    <Trash2 className="w-3.5 h-3.5 mr-1" /> Tout effacer
                  </Button>
                )}
              </div>

              <div className="min-h-[200px] max-h-[400px] overflow-y-auto pr-2 space-y-3">
                <AnimatePresence>
                  {scannedList.length > 0 ? (
                    scannedList.map((med) => (
                      <ResultCard 
                        key={med.id} 
                        medication={med} 
                        onDelete={() => removeMedication(med.id)} 
                      />
                    ))
                  ) : (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="h-full flex flex-col items-center justify-center text-center p-8 border-2 border-dashed rounded-xl"
                    >
                      <div className="p-3 rounded-full bg-muted mb-3">
                        <Pill className="w-6 h-6 text-muted-foreground" />
                      </div>
                      <p className="font-medium text-muted-foreground">Aucun médicament</p>
                      <p className="text-sm text-muted-foreground/70 max-w-[200px]">
                        Scannez votre premier médicament à gauche pour voir apparaître les consignes ici.
                      </p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
