import { motion, AnimatePresence } from "framer-motion";
import { useState, useRef } from "react";
import { Camera, Upload, X, Loader2, Pill, AlertCircle, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { mockScanMedication, mockGetProtocol, type ScannedMedication } from "@/lib/api";
import { usePatientStore } from "@/store/patientStore";
import { useToast } from "@/hooks/use-toast";

interface MedicationScannerProps {
  onMedicationScanned?: (medication: ScannedMedication) => void;
}

export function MedicationScanner({ onMedicationScanned }: MedicationScannerProps) {
  const [isScanning, setIsScanning] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [currentMedication, setCurrentMedication] = useState<ScannedMedication | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { addMedication } = usePatientStore();
  const { toast } = useToast();

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const handleFile = async (file: File) => {
    if (!file.type.startsWith("image/")) {
      toast({
        title: "Format non supporté",
        description: "Veuillez utiliser une image (JPEG, PNG, etc.)",
        variant: "destructive",
      });
      return;
    }

    setIsScanning(true);
    setIsProcessing(true);

    try {
      // Step A: OCR Scan
      const ocrResult = await mockScanMedication();

      // Step D: Get Protocol (using generic name)
      const query = `Quelle est la consigne pour le médicament ${ocrResult.subCategory} avant l'opération ?`;
      const protocolResult = await mockGetProtocol(ocrResult.subCategory);

      // Create medication object
      const medication: ScannedMedication = {
        id: Date.now().toString(),
        commercialName: ocrResult.drugName,
        genericName: ocrResult.subCategory,
        instruction: protocolResult.protocol,
        riskLevel: protocolResult.riskLevel,
        scannedAt: new Date().toISOString(),
      };

      setCurrentMedication(medication);
      addMedication(medication);
      onMedicationScanned?.(medication);

      toast({
        title: "Médicament identifié",
        description: `${ocrResult.drugName} (${ocrResult.subCategory})`,
      });
    } catch (error) {
      toast({
        title: "Erreur de scan",
        description: "Impossible d'analyser l'image. Veuillez réessayer.",
        variant: "destructive",
      });
    } finally {
      setIsScanning(false);
      setIsProcessing(false);
    }
  };

  const resetScan = () => {
    setCurrentMedication(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <div className="space-y-6">
      {/* Scanner Area */}
      <AnimatePresence mode="wait">
        {!currentMedication ? (
          <motion.div
            key="scanner"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
          >
            <Card variant="elevated" className="overflow-hidden">
              <CardHeader className="text-center pb-2">
                <CardTitle className="flex items-center justify-center gap-2">
                  <Pill className="w-6 h-6 text-primary" />
                  Scanner un médicament
                </CardTitle>
                <CardDescription>
                  Prenez une photo de votre boîte de médicaments ou téléchargez une image
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div
                  className={`
                    relative border-2 border-dashed rounded-xl p-8 md:p-12 transition-all duration-300 cursor-pointer
                    ${dragActive 
                      ? "border-primary bg-accent" 
                      : "border-muted-foreground/25 hover:border-primary/50 hover:bg-accent/50"
                    }
                    ${isProcessing ? "pointer-events-none" : ""}
                  `}
                  onDragEnter={handleDrag}
                  onDragLeave={handleDrag}
                  onDragOver={handleDrag}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    capture="environment"
                    className="hidden"
                    onChange={handleFileInput}
                  />
                  
                  <div className="flex flex-col items-center justify-center gap-4 text-center">
                    {isProcessing ? (
                      <>
                        <motion.div
                          animate={{ rotate: 360 }}
                          transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                        >
                          <Loader2 className="w-12 h-12 text-primary" />
                        </motion.div>
                        <p className="text-lg font-medium text-foreground">
                          Analyse en cours...
                        </p>
                        <p className="text-sm text-muted-foreground">
                          Identification du médicament et récupération des consignes
                        </p>
                      </>
                    ) : (
                      <>
                        <div className="flex gap-4">
                          <motion.div
                            whileHover={{ scale: 1.1 }}
                            className="p-4 rounded-full bg-primary/10"
                          >
                            <Camera className="w-8 h-8 text-primary" />
                          </motion.div>
                          <motion.div
                            whileHover={{ scale: 1.1 }}
                            className="p-4 rounded-full bg-primary/10"
                          >
                            <Upload className="w-8 h-8 text-primary" />
                          </motion.div>
                        </div>
                        <div>
                          <p className="text-lg font-medium text-foreground">
                            Glissez une image ici
                          </p>
                          <p className="text-sm text-muted-foreground mt-1">
                            ou cliquez pour prendre une photo / sélectionner un fichier
                          </p>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ) : (
          <motion.div
            key="result"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.3 }}
          >
            <Card 
              variant={currentMedication.riskLevel === "STOP" ? "danger" : "success"}
              className="overflow-hidden"
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <Badge 
                        variant={currentMedication.riskLevel === "STOP" ? "stop" : "continue"}
                        className="uppercase"
                      >
                        {currentMedication.riskLevel === "STOP" ? (
                          <><AlertCircle className="w-3 h-3 mr-1" /> STOP</>
                        ) : (
                          <><CheckCircle className="w-3 h-3 mr-1" /> CONTINUE</>
                        )}
                      </Badge>
                    </div>
                    <CardTitle className="text-xl">
                      {currentMedication.commercialName}
                    </CardTitle>
                    <CardDescription className="text-base mt-1">
                      Générique : {currentMedication.genericName}
                    </CardDescription>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={resetScan}
                    className="shrink-0"
                  >
                    <X className="w-5 h-5" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="bg-card/80 rounded-lg p-4 border">
                  <h4 className="font-medium mb-2 flex items-center gap-2">
                    <Pill className="w-4 h-4" />
                    Consignes pré-opératoires
                  </h4>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {currentMedication.instruction}
                  </p>
                </div>
                
                <Button
                  variant="medical"
                  className="w-full mt-4"
                  onClick={resetScan}
                >
                  <Camera className="w-4 h-4 mr-2" />
                  Scanner un autre médicament
                </Button>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
