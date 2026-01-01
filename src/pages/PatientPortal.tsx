import { motion } from "framer-motion";
import { MedicationScanner } from "@/components/patient/MedicationScanner";
import { FloatingChatbot } from "@/components/patient/FloatingChatbot";
import { MedicationCard } from "@/components/patient/MedicationCard";
import { usePatientStore } from "@/store/patientStore";
import { Shield, ArrowLeft, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";

export default function PatientPortal() {
  const { scannedMedications } = usePatientStore();

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-card/80 backdrop-blur-lg border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <Link to="/" className="flex items-center gap-2">
              <Button variant="ghost" size="icon">
                <ArrowLeft className="w-5 h-5" />
              </Button>
            </Link>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center">
                <Shield className="w-5 h-5 text-primary-foreground" />
              </div>
              <div>
                <h1 className="font-semibold text-foreground">AnesthesiaGuard</h1>
                <p className="text-xs text-muted-foreground">Portail Patient</p>
              </div>
            </div>
            <div className="w-10" /> {/* Spacer for alignment */}
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
          {/* Welcome Section */}
          <div className="text-center mb-8">
            <h2 className="text-2xl md:text-3xl font-bold text-foreground mb-2">
              Préparez votre dossier d'anesthésie
            </h2>
            <p className="text-muted-foreground">
              Scannez vos médicaments pour recevoir les consignes pré-opératoires personnalisées
            </p>
          </div>

          {/* Scanner */}
          <MedicationScanner />

          {/* Scanned Medications Summary */}
          {scannedMedications.length > 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.3, delay: 0.2 }}
              className="mt-8"
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
                  <FileText className="w-5 h-5 text-primary" />
                  Vos médicaments scannés
                </h3>
                <span className="text-sm text-muted-foreground">
                  {scannedMedications.length} médicament{scannedMedications.length > 1 ? "s" : ""}
                </span>
              </div>
              <div className="space-y-4">
                {scannedMedications.map((medication, index) => (
                  <MedicationCard 
                    key={medication.id} 
                    medication={medication} 
                    index={index}
                  />
                ))}
              </div>
            </motion.div>
          )}
        </motion.div>
      </main>

      {/* Floating Chatbot */}
      <FloatingChatbot />
    </div>
  );
}
