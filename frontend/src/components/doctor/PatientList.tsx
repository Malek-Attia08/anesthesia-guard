import { useState } from "react";
import { motion } from "framer-motion";
import { Search, User, Calendar, Activity, ChevronRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Patient } from "@/lib/api";
import { usePatientStore } from "@/store/patientStore";

interface PatientListProps {
  onSelectPatient: (patient: Patient) => void;
}

export function PatientList({ onSelectPatient }: PatientListProps) {
  const { patients } = usePatientStore();
  const [searchQuery, setSearchQuery] = useState("");

  const filteredPatients = patients.filter((patient) =>
    patient.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getStopCount = (patient: Patient) => {
    return patient.medications.filter((m) => m.riskLevel === "STOP").length;
  };

  return (
    <div className="space-y-6">
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
        <input
          type="text"
          placeholder="Rechercher un patient..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-12 pr-4 py-3 bg-card border rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
        />
      </div>

      {/* Patient Cards */}
      <div className="grid gap-4">
        {filteredPatients.map((patient, index) => (
          <motion.div
            key={patient.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: index * 0.1 }}
          >
            <Card 
              variant="elevated" 
              className="cursor-pointer hover:border-primary/50 transition-colors"
              onClick={() => onSelectPatient(patient)}
            >
              <CardContent className="p-4">
                <div className="flex items-center gap-4">
                  {/* Avatar */}
                  <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                    <User className="w-6 h-6 text-primary" />
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-semibold text-foreground truncate">
                        {patient.name}
                      </h3>
                      <Badge variant="asa" className="shrink-0">
                        {patient.asaScore}
                      </Badge>
                    </div>
                    <div className="flex flex-wrap gap-3 text-sm text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5" />
                        {patient.age} ans
                      </span>
                      <span className="flex items-center gap-1">
                        <Activity className="w-3.5 h-3.5" />
                        {patient.operationType}
                      </span>
                    </div>
                  </div>

                  {/* Medication Stats */}
                  <div className="flex items-center gap-3 shrink-0">
                    <div className="text-right">
                      <p className="text-sm font-medium">
                        {patient.medications.length} médicament{patient.medications.length > 1 ? "s" : ""}
                      </p>
                      {getStopCount(patient) > 0 && (
                        <p className="text-xs text-medical-red">
                          {getStopCount(patient)} à arrêter
                        </p>
                      )}
                    </div>
                    <ChevronRight className="w-5 h-5 text-muted-foreground" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}

        {filteredPatients.length === 0 && (
          <div className="text-center py-12 text-muted-foreground">
            <User className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>Aucun patient trouvé</p>
          </div>
        )}
      </div>
    </div>
  );
}
