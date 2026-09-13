import { motion } from "framer-motion";
import { Shield, Pill, MessageCircle, Camera, ArrowLeft, Video, UserCircle, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Link } from "react-router-dom";

const menuItems = [
  {
    title: "Scanner mes médicaments",
    description: "Photographiez vos boîtes pour les consignes pré-op",
    icon: Pill,
    path: "/patient/scanner",
    color: "from-sky-500 to-blue-600",
    bgColor: "bg-sky-50 dark:bg-sky-950/30",
  },
  {
    title: "Consultation IA",
    description: "Discutez avec notre assistant pour préparer l'anesthésie",
    icon: MessageCircle,
    path: "/patient/consultation",
    color: "from-emerald-500 to-teal-600",
    bgColor: "bg-emerald-50 dark:bg-emerald-950/30",
  },
  {
    title: "Évaluation Mallampati",
    description: "Photo de votre bouche pour évaluer le score",
    icon: Camera,
    path: "/patient/mallampati",
    color: "from-amber-500 to-orange-600",
    bgColor: "bg-amber-50 dark:bg-amber-950/30",
  },
  {
    title: "Réunion avec le Docteur",
    description: "Rejoignez la visio pour l'évaluation préopératoire",
    icon: Video,
    path: "/patient/reunion",
    color: "from-rose-500 to-pink-600",
    bgColor: "bg-rose-50 dark:bg-rose-950/30",
  },
  {
    title: "Mon Profil & Score ASA",
    description: "Consultez vos infos et calculez votre risque",
    icon: UserCircle,
    path: "/patient/asa",
    color: "from-indigo-500 to-violet-600",
    bgColor: "bg-indigo-50 dark:bg-indigo-950/30",
  },
  {
    title: "Détection d'émotion",
    description: "Analysez vos émotions via la caméra pour le suivi",
    icon: Camera,
    path: "/patient/emotion",
    color: "from-fuchsia-500 to-purple-600",
    bgColor: "bg-fuchsia-50 dark:bg-fuchsia-950/30",
  },
];

export default function PatientHome() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-muted/30">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-card/80 backdrop-blur-lg border-b">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <Link to="/">
              <Button variant="ghost" size="icon" className="rounded-full">
                <ArrowLeft className="w-5 h-5" />
              </Button>
            </Link>
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl gradient-primary flex items-center justify-center">
                <Shield className="w-5 h-5 text-primary-foreground" />
              </div>
              <span className="font-semibold text-foreground">AnesthesiaGuard</span>
            </div>
            <div className="w-10" />
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-8 md:py-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-center max-w-2xl mx-auto mb-10"
        >
          <div className="inline-flex items-center gap-2 bg-primary/10 text-primary px-4 py-1.5 rounded-full text-sm font-medium mb-4">
            <Shield className="w-4 h-4" />
            Portail Patient
          </div>
          <h1 className="text-3xl md:text-4xl font-bold text-foreground mb-3">
            Bienvenue sur votre espace
          </h1>
          <p className="text-muted-foreground text-lg">
            Préparez votre consultation d'anesthésie en quelques étapes simples
          </p>
        </motion.div>

        {/* Grid Layout */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6 max-w-5xl mx-auto">
          {menuItems.map((item, index) => (
            <motion.div
              key={item.path}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: index * 0.08 }}
              className={index === 0 ? "md:col-span-2 lg:col-span-1" : ""}
            >
              <Link to={item.path} className="block h-full">
                <Card className={`group h-full hover:shadow-xl transition-all duration-300 hover:-translate-y-1 border-2 hover:border-primary/20 ${item.bgColor}`}>
                  <CardContent className="p-6 flex flex-col h-full">
                    <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${item.color} flex items-center justify-center shadow-lg mb-4 group-hover:scale-110 transition-transform duration-300`}>
                      <item.icon className="w-7 h-7 text-white" />
                    </div>
                    <h3 className="text-lg font-semibold text-foreground mb-2 group-hover:text-primary transition-colors">
                      {item.title}
                    </h3>
                    <p className="text-sm text-muted-foreground flex-1">
                      {item.description}
                    </p>
                    <div className="flex items-center gap-1 text-primary font-medium text-sm mt-4 opacity-0 group-hover:opacity-100 transition-opacity">
                      Accéder <ArrowRight className="w-4 h-4" />
                    </div>
                  </CardContent>
                </Card>
              </Link>
            </motion.div>
          ))}
        </div>
      </section>
    </div>
  );
}
