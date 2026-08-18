import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";

const headlineWords = ["Turn", "Raw", "Data", "Into", "Clean", "Intelligence"];

const Hero = () => {
  const scrollToUpload = () => {
    const el = document.getElementById("upload-section");
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <section className="relative overflow-hidden py-20 sm:py-28">
      {/* Animated gradient background */}
      <div className="absolute inset-0 -z-10 pointer-events-none">
        <motion.div
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full opacity-20 blur-[120px]"
          style={{
            background:
              "radial-gradient(circle, hsl(190 90% 50%), transparent 70%)",
          }}
          animate={{ scale: [1, 1.15, 1], rotate: [0, 45, 0] }}
          transition={{
            duration: 12,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />

        <motion.div
          className="absolute top-1/3 right-1/4 w-[400px] h-[400px] rounded-full opacity-10 blur-[100px]"
          style={{
            background:
              "radial-gradient(circle, hsl(210 80% 60%), transparent 70%)",
          }}
          animate={{ scale: [1.1, 1, 1.1], x: [0, 30, 0] }}
          transition={{
            duration: 10,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 text-center">
        {/* Headline */}
        <motion.h1
          className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-foreground leading-tight"
          initial="hidden"
          animate="visible"
          variants={{
            visible: {
              transition: { staggerChildren: 0.08 },
            },
          }}
        >
          {headlineWords.map((word, i) => (
            <motion.span
              key={i}
              className={`inline-block mr-3 ${
                i >= 4 ? "glow-text text-primary" : ""
              }`}
              variants={{
                hidden: {
                  opacity: 0,
                  y: 30,
                  filter: "blur(8px)",
                },
                visible: {
                  opacity: 1,
                  y: 0,
                  filter: "blur(0px)",
                  transition: {
                    duration: 0.5,
                    ease: "easeOut",
                  },
                },
              }}
            >
              {word}
            </motion.span>
          ))}
        </motion.h1>

        {/* Subheading */}
        <motion.p
          className="mt-6 text-lg sm:text-xl text-muted-foreground max-w-2xl mx-auto"
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, duration: 0.6 }}
        >
          AI-powered dataset cleaning for faster and smarter workflows.
        </motion.p>

        {/* CTA Button */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.9, duration: 0.5 }}
          className="mt-10"
        >
          <button
            onClick={scrollToUpload}
            className="group relative inline-flex items-center gap-2 bg-primary text-primary-foreground font-semibold rounded-xl px-7 py-3.5 text-sm transition-all hover:shadow-[0_0_30px_hsl(190_90%_50%/0.4)] hover:scale-[1.03] active:scale-[0.98]"
          >
            Get Started
            <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
          </button>
        </motion.div>
      </div>
    </section>
  );
};

export default Hero;