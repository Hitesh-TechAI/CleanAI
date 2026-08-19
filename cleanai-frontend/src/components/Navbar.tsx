import { CheckCircle2 } from "lucide-react";
import { useEffect, useState } from "react";

const BACKEND_URL = "https://cleanai-1-lmjm.onrender.com" || "http://127.0.0.1:8000";

const Navbar = () => {
  const [scrolled, setScrolled] = useState(false);
  const [datasetLoaded, setDatasetLoaded] = useState(false);
  const [backendOnline, setBackendOnline] = useState(false);

  // Detect scroll
  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 10);
    };

    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // Check backend status
  useEffect(() => {
    const checkBackend = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}`);
        if (res.ok) setBackendOnline(true);
      } catch {
        setBackendOnline(false);
      }
    };

    checkBackend();
  }, []);

  // Listen for dataset upload
  useEffect(() => {
    const handleDatasetUpdate = () => {
      setDatasetLoaded(true);
    };

    window.addEventListener("dataset-updated", handleDatasetUpdate);

    return () => {
      window.removeEventListener("dataset-updated", handleDatasetUpdate);
    };
  }, []);

  return (
    <nav
      className={`sticky top-0 z-50 px-6 py-4 flex items-center justify-between transition-all duration-300 ${
        scrolled
          ? "backdrop-blur-md bg-background/80 shadow-lg border-b border-border"
          : "glass border-b border-border"
      }`}
    >
      {/* Left Section */}
      <div className="flex items-center gap-3">
        <span className="text-2xl">🧠</span>
        <div>
          <h1 className="text-lg font-semibold text-foreground tracking-tight">
            CleanAI
          </h1>
          <p className="text-xs text-muted-foreground">
            Conversational AI Data Cleaning Agent
          </p>
        </div>
      </div>

      {/* Right Section */}
      <div className="flex items-center gap-3">
        {/* Dataset Badge */}
        {datasetLoaded && (
          <span className="inline-flex items-center gap-1.5 text-xs font-medium bg-success/15 text-success border border-success/20 rounded-full px-3 py-1 animate-fade-in">
            <CheckCircle2 className="w-3 h-3" />
            Dataset Loaded
          </span>
        )}

        {/* Backend Status */}
        <span
          className={`text-xs font-mono ${
            backendOnline ? "text-primary" : "text-destructive"
          }`}
        >
          ● {backendOnline ? "Online" : "Offline"}
        </span>
      </div>
    </nav>
  );
};

export default Navbar;
