import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { AlertCircle, CheckCircle, Pill } from "lucide-react";
import { ScannedMedication } from "@/lib/api";
import { motion } from "framer-motion";

interface MedicationCardProps {
  medication: ScannedMedication;
  index?: number;
}

export function MedicationCard({ medication, index = 0 }: MedicationCardProps) {
  const isStop = medication.riskLevel === "STOP";

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.1 }}
    >
      <Card variant={isStop ? "danger" : "success"}>
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              <CardTitle className="text-lg truncate">
                {medication.commercialName}
              </CardTitle>
              <CardDescription className="mt-1">
                Générique : {medication.genericName}
              </CardDescription>
            </div>
            <Badge 
              variant={isStop ? "stop" : "continue"}
              className="shrink-0 uppercase"
            >
              {isStop ? (
                <><AlertCircle className="w-3 h-3 mr-1" /> STOP</>
              ) : (
                <><CheckCircle className="w-3 h-3 mr-1" /> CONTINUE</>
              )}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="bg-card/80 rounded-lg p-3 border">
            <div className="flex items-start gap-2">
              <Pill className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
              <p className="text-sm text-muted-foreground leading-relaxed">
                {medication.instruction}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
