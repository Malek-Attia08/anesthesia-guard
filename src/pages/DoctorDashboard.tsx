import { useState } from "react";
import { motion } from "framer-motion";
import { PatientList } from "@/components/doctor/PatientList";
import { PatientFile } from "@/components/doctor/PatientFile";
import { Patient } from "@/lib/api";
import { Shield, ArrowLeft, Users, LayoutDashboard } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";

export default function DoctorDashboard() {
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);

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
                <p className="text-xs text-muted-foreground">Tableau de bord Médecin</p>
              </div>
            </div>
            <div className="w-10" /> {/* Spacer for alignment */}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          {!selectedPatient ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.3 }}
            >
              {/* Dashboard Header */}
              <div className="flex items-center justify-between mb-8">
                <div>
                  <h2 className="text-2xl md:text-3xl font-bold text-foreground flex items-center gap-3">
                    <LayoutDashboard className="w-8 h-8 text-primary" />
                    Tableau de bord
                  </h2>
                  <p className="text-muted-foreground mt-1">
                    Gérez vos patients et consultez leurs dossiers médicaux en temps réel
                  </p>
                </div>
              </div>

              {/* Stats Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: 0.1 }}
                  className="bg-card rounded-xl p-4 border shadow-soft"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center">
                      <Users className="w-6 h-6 text-primary" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-foreground">3</p>
                      <p className="text-sm text-muted-foreground">Patients actifs</p>
                    </div>
                  </div>
                </motion.div>
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: 0.2 }}
                  className="bg-card rounded-xl p-4 border shadow-soft"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-lg bg-medical-red-light flex items-center justify-center">
                      <span className="text-lg font-bold text-medical-red">3</span>
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-foreground">3</p>
                      <p className="text-sm text-muted-foreground">Médicaments à arrêter</p>
                    </div>
                  </div>
                </motion.div>
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: 0.3 }}
                  className="bg-card rounded-xl p-4 border shadow-soft"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-lg bg-medical-green-light flex items-center justify-center">
                      <span className="text-lg font-bold text-medical-green">3</span>
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-foreground">3</p>
                      <p className="text-sm text-muted-foreground">Peuvent continuer</p>
                    </div>
                  </div>
                </motion.div>
              </div>

              {/* Patient List */}
              <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                <Users className="w-5 h-5 text-primary" />
                Liste des patients
              </h3>
              <PatientList onSelectPatient={setSelectedPatient} />
            </motion.div>
          ) : (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3 }}
            >
              <PatientFile
                patient={selectedPatient}
                onBack={() => setSelectedPatient(null)}
              />
            </motion.div>
          )}
        </div>
      </main>
    </div>
  );
}
