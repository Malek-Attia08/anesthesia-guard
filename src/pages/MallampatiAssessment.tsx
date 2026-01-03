import { motion } from "framer-motion";
import { ArrowLeft, Camera, Upload, Info, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Link } from "react-router-dom";
import { useState, useRef } from "react";

interface MallampatiResult {
  score: number;
  description: string;
  interpretation: string;
}

const mallampatiInfo = [
  { score: 1, description: "Palais mou, luette et piliers visibles", risk: "Faible" },
  { score: 2, description: "Palais mou et luette visibles", risk: "Faible" },
  { score: 3, description: "Palais mou et base de la luette visibles", risk: "Modéré" },
  { score: 4, description: "Palais mou non visible", risk: "Élevé" },
];

export default function MallampatiAssessment() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState<MallampatiResult | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (file: File) => {
    if (!file.type.startsWith("image/")) return;

    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    setIsProcessing(true);

    // Simulate API call for Mallampati classification
    await new Promise((resolve) => setTimeout(resolve, 2000));

    // Mock result - in real app, this would come from an ML model
    const mockScore = Math.floor(Math.random() * 4) + 1;
    const info = mallampatiInfo[mockScore - 1];
    
    setResult({
      score: mockScore,
      description: info.description,
      interpretation: `Votre score Mallampati est de classe ${mockScore}. ${
        mockScore <= 2
          ? "L'intubation devrait être relativement simple."
          : "Une intubation potentiellement difficile est à prévoir. L'anesthésiste prendra les précautions nécessaires."
      }`,
    });
    setIsProcessing(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleFileUpload(file);
  };

  const resetAssessment = () => {
    setResult(null);
    setPreviewUrl(null);
  };

  const getScoreColor = (score: number) => {
    if (score <= 2) return "bg-emerald-500";
    if (score === 3) return "bg-amber-500";
    return "bg-red-500";
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-card/80 backdrop-blur-lg border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <Link to="/patient" className="flex items-center gap-2">
              <Button variant="ghost" size="icon">
                <ArrowLeft className="w-5 h-5" />
              </Button>
            </Link>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-amber-600 flex items-center justify-center">
                <Camera className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="font-semibold text-foreground">Mallampati</h1>
                <p className="text-xs text-muted-foreground">Évaluation</p>
              </div>
            </div>
            <div className="w-10" />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="max-w-xl mx-auto"
        >
          {/* Instructions */}
          <Card className="mb-6 border-amber-200 bg-amber-50/50">
            <CardContent className="p-4">
              <div className="flex gap-3">
                <Info className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-amber-800">Comment prendre la photo</p>
                  <ul className="text-sm text-amber-700 mt-2 space-y-1">
                    <li>• Ouvrez grand la bouche</li>
                    <li>• Tirez la langue sans dire "Ahh"</li>
                    <li>• Assurez un bon éclairage</li>
                    <li>• Cadrez sur votre bouche ouverte</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>

          {!result ? (
            <>
              {/* Upload Area */}
              <Card
                className={`border-2 border-dashed transition-colors ${
                  isProcessing ? "border-primary bg-primary/5" : "border-muted-foreground/25 hover:border-primary/50"
                }`}
                onDrop={handleDrop}
                onDragOver={(e) => e.preventDefault()}
              >
                <CardContent className="p-8">
                  {isProcessing ? (
                    <div className="text-center py-8">
                      {previewUrl && (
                        <img
                          src={previewUrl}
                          alt="Preview"
                          className="w-32 h-32 object-cover rounded-xl mx-auto mb-4"
                        />
                      )}
                      <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
                      <p className="text-foreground font-medium">Analyse en cours...</p>
                      <p className="text-sm text-muted-foreground mt-1">
                        Classification du score Mallampati
                      </p>
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <div className="w-16 h-16 rounded-full bg-amber-100 flex items-center justify-center mx-auto mb-4">
                        <Camera className="w-8 h-8 text-amber-600" />
                      </div>
                      <p className="text-foreground font-medium mb-2">
                        Prenez une photo de votre bouche ouverte
                      </p>
                      <p className="text-sm text-muted-foreground mb-6">
                        Glissez-déposez une image ou utilisez le bouton ci-dessous
                      </p>
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept="image/*"
                        capture="environment"
                        className="hidden"
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) handleFileUpload(file);
                        }}
                      />
                      <div className="flex gap-3 justify-center">
                        <Button
                          onClick={() => fileInputRef.current?.click()}
                          className="gap-2"
                        >
                          <Camera className="w-4 h-4" />
                          Prendre une photo
                        </Button>
                        <Button
                          variant="outline"
                          onClick={() => fileInputRef.current?.click()}
                          className="gap-2"
                        >
                          <Upload className="w-4 h-4" />
                          Importer
                        </Button>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Score Reference */}
              <div className="mt-8">
                <h3 className="text-sm font-medium text-muted-foreground mb-3">
                  Référence des scores Mallampati
                </h3>
                <div className="grid grid-cols-2 gap-3">
                  {mallampatiInfo.map((info) => (
                    <Card key={info.score} className="p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <div className={`w-6 h-6 rounded-full ${getScoreColor(info.score)} text-white text-xs font-bold flex items-center justify-center`}>
                          {info.score}
                        </div>
                        <Badge variant={info.risk === "Faible" ? "continue" : info.risk === "Modéré" ? "outline" : "stop"}>
                          {info.risk}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground">{info.description}</p>
                    </Card>
                  ))}
                </div>
              </div>
            </>
          ) : (
            /* Result Display */
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3 }}
            >
              <Card className="overflow-hidden">
                {previewUrl && (
                  <div className="relative h-48 bg-muted">
                    <img
                      src={previewUrl}
                      alt="Mallampati assessment"
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
                    <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between">
                      <Badge className="text-lg px-4 py-1" variant={result.score <= 2 ? "continue" : "stop"}>
                        Classe {result.score}
                      </Badge>
                    </div>
                  </div>
                )}
                <CardContent className="p-6">
                  <div className="flex items-start gap-3 mb-4">
                    <div className={`w-12 h-12 rounded-full ${getScoreColor(result.score)} text-white text-xl font-bold flex items-center justify-center`}>
                      {result.score}
                    </div>
                    <div>
                      <h3 className="font-semibold text-lg">Score Mallampati {result.score}</h3>
                      <p className="text-sm text-muted-foreground">{result.description}</p>
                    </div>
                  </div>
                  <Card className="bg-muted/50 border-0">
                    <CardContent className="p-4">
                      <p className="text-sm">{result.interpretation}</p>
                    </CardContent>
                  </Card>
                  <div className="flex items-center gap-2 mt-4 text-sm text-emerald-600">
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Résultat enregistré dans votre dossier</span>
                  </div>
                </CardContent>
              </Card>

              <Button
                onClick={resetAssessment}
                variant="outline"
                className="w-full mt-4"
              >
                Refaire l'évaluation
              </Button>
            </motion.div>
          )}
        </motion.div>
      </main>
    </div>
  );
}
