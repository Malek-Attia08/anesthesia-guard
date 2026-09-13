import { motion } from "framer-motion";
import { ArrowLeft, User, Calendar, Activity, AlertCircle, CheckCircle, Pill, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Patient } from "@/lib/api";
import { useState } from "react";

interface PatientFileProps {
  patient: Patient;
  onBack: () => void;
}

export function PatientFile({ patient, onBack }: PatientFileProps) {
  const [isRefreshingASA, setIsRefreshingASA] = useState(false);
  
  const stopMeds = patient.medications.filter((m) => m.riskLevel === "STOP");
  const continueMeds = patient.medications.filter((m) => m.riskLevel === "CONTINUE");

  const handleRefreshASA = async () => {
    setIsRefreshingASA(true);
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000));
    setIsRefreshingASA(false);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={onBack}>
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-foreground">
            Dossier Patient
          </h1>
          <p className="text-muted-foreground">Suivi en temps réel</p>
        </div>
      </div>

      {/* Patient Info Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <Card variant="medical">
          <CardContent className="p-6">
            <div className="flex items-start gap-4">
              <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                <User className="w-8 h-8 text-primary" />
              </div>
              <div className="flex-1">
                <h2 className="text-xl font-semibold text-foreground mb-2">
                  {patient.name}
                </h2>
                <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                  <span className="flex items-center gap-1.5">
                    <Calendar className="w-4 h-4" />
                    {patient.age} ans
                  </span>
                  <span className="flex items-center gap-1.5">
                    <Activity className="w-4 h-4" />
                    {patient.operationType}
                  </span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* ASA Score Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.1 }}
      >
        <Card variant="elevated">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-lg">Score ASA</CardTitle>
                <CardDescription>
                  Classification de l'état physique préopératoire
                </CardDescription>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleRefreshASA}
                disabled={isRefreshingASA}
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${isRefreshingASA ? "animate-spin" : ""}`} />
                Recalculer
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-4">
              <div className="w-20 h-20 rounded-xl gradient-primary flex items-center justify-center">
                <span className="text-2xl font-bold text-primary-foreground">
                  {patient.asaScore.replace("ASA ", "")}
                </span>
              </div>
              <div>
                <p className="text-2xl font-bold text-foreground">{patient.asaScore}</p>
                <p className="text-sm text-muted-foreground">
                  {patient.asaScore === "ASA I" && "Patient en bonne santé"}
                  {patient.asaScore === "ASA II" && "Maladie systémique légère"}
                  {patient.asaScore === "ASA III" && "Maladie systémique sévère"}
                  {patient.asaScore === "ASA IV" && "Maladie menaçant le pronostic vital"}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Medications to STOP */}
      {stopMeds.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.2 }}
        >
          <h3 className="text-lg font-semibold text-destructive mb-3 flex items-center gap-2">
            <AlertCircle className="w-5 h-5" />
            Médicaments à arrêter ({stopMeds.length})
          </h3>
          <div className="space-y-3">
            {stopMeds.map((med, index) => (
              <Card key={med.id} variant="danger">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-semibold text-foreground">
                          {med.commercialName}
                        </span>
                        <Badge variant="stop">STOP</Badge>
                      </div>
                      <p className="text-sm text-muted-foreground mb-2">
                        Générique : {med.genericName}
                      </p>
                      <div className="bg-card/50 rounded-lg p-3 text-sm">
                        <div className="flex items-start gap-2">
                          <Pill className="w-4 h-4 mt-0.5 shrink-0" />
                          <p>{med.instruction}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </motion.div>
      )}

      {/* Medications to CONTINUE */}
      {continueMeds.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.3 }}
        >
          <h3 className="text-lg font-semibold text-success mb-3 flex items-center gap-2">
            <CheckCircle className="w-5 h-5" />
            Médicaments à continuer ({continueMeds.length})
          </h3>
          <div className="space-y-3">
            {continueMeds.map((med, index) => (
              <Card key={med.id} variant="success">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-semibold text-foreground">
                          {med.commercialName}
                        </span>
                        <Badge variant="continue">CONTINUE</Badge>
                      </div>
                      <p className="text-sm text-muted-foreground mb-2">
                        Générique : {med.genericName}
                      </p>
                      <div className="bg-card/50 rounded-lg p-3 text-sm">
                        <div className="flex items-start gap-2">
                          <Pill className="w-4 h-4 mt-0.5 shrink-0" />
                          <p>{med.instruction}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </motion.div>
      )}

      {/* Empty State */}
      {patient.medications.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center">
            <Pill className="w-12 h-12 mx-auto mb-4 text-muted-foreground opacity-50" />
            <p className="text-muted-foreground">
              Aucun médicament scanné par le patient
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
