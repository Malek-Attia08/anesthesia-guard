import { create } from "zustand";
import { Patient, ScannedMedication, mockPatients } from "@/lib/api";

interface PatientStore {
  patients: Patient[];
  currentPatient: Patient | null;
  scannedMedications: ScannedMedication[];
  setCurrentPatient: (patient: Patient | null) => void;
  addMedication: (medication: ScannedMedication) => void;
  clearMedications: () => void;
  updatePatientASA: (patientId: string, asaScore: string) => void;
  addMedicationToPatient: (patientId: string, medication: ScannedMedication) => void;
}

export const usePatientStore = create<PatientStore>((set) => ({
  patients: mockPatients,
  currentPatient: null,
  scannedMedications: [],
  
  setCurrentPatient: (patient) => set({ currentPatient: patient }),
  
  addMedication: (medication) =>
    set((state) => ({
      scannedMedications: [...state.scannedMedications, medication],
    })),
  
  clearMedications: () => set({ scannedMedications: [] }),
  
  updatePatientASA: (patientId, asaScore) =>
    set((state) => ({
      patients: state.patients.map((p) =>
        p.id === patientId ? { ...p, asaScore } : p
      ),
    })),
  
  addMedicationToPatient: (patientId, medication) =>
    set((state) => ({
      patients: state.patients.map((p) =>
        p.id === patientId
          ? { ...p, medications: [...p.medications, medication] }
          : p
      ),
    })),
}));
