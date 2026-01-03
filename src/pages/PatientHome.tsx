import { motion } from "framer-motion";
import { Shield, Pill, MessageCircle, Camera, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Link } from "react-router-dom";

const menuItems = [
  {
    title: "Scanner mes médicaments",
    description: "Photographiez vos boîtes de médicaments pour recevoir les consignes pré-opératoires",
    icon: Pill,
    path: "/patient/scanner",
    color: "from-primary to-primary/80",
  },
  {
    title: "Commencer la consultation",
    description: "Discutez avec notre assistant IA pour préparer votre anesthésie",
    icon: MessageCircle,
    path: "/patient/consultation",
    color: "from-emerald-500 to-emerald-600",
  },
  {
    title: "Évaluation Mallampati",
    description: "Prenez une photo de votre bouche ouverte pour évaluer votre score Mallampati",
    icon: Camera,
    path: "/patient/mallampati",
    color: "from-amber-500 to-amber-600",
  },
];

export default function PatientHome() {
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
          className="max-w-2xl mx-auto"
        >
          {/* Welcome Section */}
          <div className="text-center mb-10">
            <h2 className="text-2xl md:text-3xl font-bold text-foreground mb-3">
              Bienvenue sur votre espace patient
            </h2>
            <p className="text-muted-foreground">
              Préparez votre consultation d'anesthésie en quelques étapes simples
            </p>
          </div>

          {/* Menu Cards */}
          <div className="space-y-4">
            {menuItems.map((item, index) => (
              <motion.div
                key={item.path}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3, delay: index * 0.1 }}
              >
                <Link to={item.path}>
                  <Card className="group hover:shadow-lg transition-all duration-300 hover:scale-[1.02] cursor-pointer border-2 hover:border-primary/30">
                    <CardContent className="p-6">
                      <div className="flex items-center gap-5">
                        <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${item.color} flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform duration-300`}>
                          <item.icon className="w-7 h-7 text-white" />
                        </div>
                        <div className="flex-1">
                          <h3 className="text-lg font-semibold text-foreground group-hover:text-primary transition-colors">
                            {item.title}
                          </h3>
                          <p className="text-sm text-muted-foreground mt-1">
                            {item.description}
                          </p>
                        </div>
                        <div className="text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all">
                          <ArrowLeft className="w-5 h-5 rotate-180" />
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </main>
    </div>
  );
}
