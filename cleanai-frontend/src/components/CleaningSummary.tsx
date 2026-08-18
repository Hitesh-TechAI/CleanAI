import { Download, CheckCircle2, Trash2, TrendingUp, Search } from "lucide-react";
import { useState } from "react";

const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL || "http://127.0.0.1:8000";

interface SummaryItem {
  icon: any;
  label: string;
  value: string;
  color: string;
}

const CleaningSummary = () => {
  const [summaryItems, setSummaryItems] = useState<SummaryItem[]>([]);
  const [qualityBefore, setQualityBefore] = useState<string | null>(null);
  const [qualityAfter, setQualityAfter] = useState<string | null>(null);

  const downloadCSV = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/download`);
      const blob = await response.blob();

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "cleaned_dataset.csv";
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (error) {
      console.error("Download failed:", error);
    }
  };

  return (
    <div className="glass rounded-lg p-5 gradient-border animate-slide-up">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-sm font-semibold text-foreground">
            Cleaning Summary
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Overview of all cleaning operations
          </p>
        </div>
        <button
          onClick={downloadCSV}
          className="bg-primary text-primary-foreground rounded-lg px-4 py-2 text-sm font-medium hover:opacity-90 transition-opacity flex items-center gap-2"
        >
          <Download className="w-4 h-4" />
          Download Cleaned CSV
        </button>
      </div>

      {summaryItems.length === 0 ? (
        <div className="bg-secondary/50 rounded-lg p-6 text-center text-sm text-muted-foreground">
          No cleaning operations performed yet.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {summaryItems.map((item) => (
            <div key={item.label} className="bg-secondary/50 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-1">
                <item.icon className={`w-4 h-4 ${item.color}`} />
                <span className="text-xs text-muted-foreground">
                  {item.label}
                </span>
              </div>
              <p className="text-lg font-semibold text-foreground font-mono">
                {item.value}
              </p>
            </div>
          ))}

          {qualityBefore && qualityAfter && (
            <div className="bg-secondary/50 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-1">
                <TrendingUp className="w-4 h-4 text-primary" />
                <span className="text-xs text-muted-foreground">
                  Quality Score
                </span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-xs text-muted-foreground line-through font-mono">
                  {qualityBefore}
                </span>
                <span className="text-lg font-semibold text-success font-mono">
                  {qualityAfter}
                </span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default CleaningSummary;