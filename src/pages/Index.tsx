import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { Shield, User, Stethoscope, ArrowRight, Heart, FileText, Activity } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

const Index = () => {
  return (
    <div className="min-h-screen gradient-hero">
      {/* Header */}
      <header className="container mx-auto px-4 py-6">
        <div className="flex items-center justify-center gap-3">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", duration: 0.6 }}
            className="w-12 h-12 rounded-xl gradient-primary flex items-center justify-center shadow-medium"
          >
            <Shield className="w-6 h-6 text-primary-foreground" />
          </motion.div>
          <motion.h1
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="text-2xl font-bold text-foreground"
          >
            AnesthesiaGuard
          </motion.h1>
        </div>
      </header>

      {/* Hero Section */}
      <main className="container mx-auto px-4 py-12 md:py-20">
        <div className="max-w-3xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
          >
            <h2 className="text-3xl md:text-5xl font-bold text-foreground mb-4 leading-tight">
              Préparez votre anesthésie
              <span className="text-primary"> en toute sérénité</span>
            </h2>
            <p className="text-lg md:text-xl text-muted-foreground mb-12 max-w-2xl mx-auto">
              Scannez vos médicaments et recevez instantanément les consignes préopératoires personnalisées grâce à notre IA médicale.
            </p>
          </motion.div>

          {/* Role Selection Cards */}
          <div className="grid md:grid-cols-2 gap-6 max-w-2xl mx-auto">
            {/* Patient Card */}
            <motion.div
              initial={{ opacity: 0, x: -30 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 0.5 }}
            >
              <Link to="/patient">
                <Card 
                  variant="elevated" 
                  className="group cursor-pointer hover:border-primary/50 transition-all duration-300 h-full"
                >
                  <CardContent className="p-8 flex flex-col items-center text-center">
                    <div className="w-20 h-20 rounded-2xl bg-primary/10 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                      <User className="w-10 h-10 text-primary" />
                    </div>
                    <h3 className="text-xl font-semibold text-foreground mb-2">
                      Je suis Patient
                    </h3>
                    <p className="text-muted-foreground text-sm mb-6">
                      Scannez vos médicaments et préparez votre dossier d'anesthésie
                    </p>
                    <Button variant="medical" className="w-full group-hover:shadow-large">
                      Accéder au portail
                      <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
                    </Button>
                  </CardContent>
                </Card>
              </Link>
            </motion.div>

            {/* Doctor Card */}
            <motion.div
              initial={{ opacity: 0, x: 30 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 0.6 }}
            >
              <Link to="/doctor">
                <Card 
                  variant="elevated" 
                  className="group cursor-pointer hover:border-primary/50 transition-all duration-300 h-full"
                >
                  <CardContent className="p-8 flex flex-col items-center text-center">
                    <div className="w-20 h-20 rounded-2xl bg-success/10 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                      <Stethoscope className="w-10 h-10 text-success" />
                    </div>
                    <h3 className="text-xl font-semibold text-foreground mb-2">
                      Je suis Médecin
                    </h3>
                    <p className="text-muted-foreground text-sm mb-6">
                      Consultez les dossiers patients et les scores ASA en temps réel
                    </p>
                    <Button variant="medical-success" className="w-full group-hover:shadow-large">
                      Accéder au tableau de bord
                      <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
                    </Button>
                  </CardContent>
                </Card>
              </Link>
            </motion.div>
          </div>

          {/* Features */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.8 }}
            className="mt-16 grid grid-cols-3 gap-6 max-w-lg mx-auto"
          >
            <div className="text-center">
              <div className="w-12 h-12 rounded-xl bg-card border shadow-soft flex items-center justify-center mx-auto mb-3">
                <Heart className="w-5 h-5 text-primary" />
              </div>
              <p className="text-sm text-muted-foreground">Sécurisé</p>
            </div>
            <div className="text-center">
              <div className="w-12 h-12 rounded-xl bg-card border shadow-soft flex items-center justify-center mx-auto mb-3">
                <FileText className="w-5 h-5 text-primary" />
              </div>
              <p className="text-sm text-muted-foreground">Intelligent</p>
            </div>
            <div className="text-center">
              <div className="w-12 h-12 rounded-xl bg-card border shadow-soft flex items-center justify-center mx-auto mb-3">
                <Activity className="w-5 h-5 text-primary" />
              </div>
              <p className="text-sm text-muted-foreground">Temps réel</p>
            </div>
          </motion.div>
        </div>
      </main>

      {/* Footer */}
      <footer className="container mx-auto px-4 py-8 text-center">
        <p className="text-sm text-muted-foreground">
          © 2024 AnesthesiaGuard — Application à usage démonstratif uniquement
        </p>
      </footer>
    </div>
  );
};

export default Index;
