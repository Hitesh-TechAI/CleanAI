import { Rows3, Columns3, AlertTriangle, Copy } from "lucide-react";
import { useEffect, useState } from "react";
import AnimatedCounter from "./AnimatedCounter";

const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL || "http://127.0.0.1:8000";

interface StatsData {
  rows: number;
  columns: number;
  missing_percent: number;
  duplicates: number;
}

const DatasetStats = () => {
  const [stats, setStats] = useState<StatsData | null>(null);

  const fetchStats = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/stats`);
      const data = await response.json();

      if (!data.error) {
        setStats(data);
      }
    } catch (error) {
      console.error("Stats fetch failed:", error);
    }
  };

  useEffect(() => {
  fetchStats();

  const refresh = () => fetchStats();

  window.addEventListener("dataset-updated", refresh);

  return () => {
    window.removeEventListener("dataset-updated", refresh);
  };
}, []);

  if (!stats) {
    return (
      <div className="grid grid-cols-2 gap-3">
        <div className="glass rounded-lg p-4 text-sm text-muted-foreground">
          No dataset loaded.
        </div>
      </div>
    );
  }

  const statItems = [
    { label: "Rows", value: stats.rows.toLocaleString(), icon: Rows3 },
    { label: "Columns", value: String(stats.columns), icon: Columns3 },
    {
      label: "Missing %",
      value: `${stats.missing_percent}%`,
      icon: AlertTriangle,
    },
    {
      label: "Duplicates",
      value: String(stats.duplicates),
      icon: Copy,
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-3">
      {statItems.map((stat, i) => (
        <div
          key={stat.label}
          className="glass rounded-lg p-4 gradient-border animate-fade-in"
          style={{ animationDelay: `${i * 100}ms` }}
        >
          <div className="flex items-center gap-2 mb-1">
            <stat.icon className="w-3.5 h-3.5 text-primary" />
            <span className="text-xs text-muted-foreground">
              {stat.label}
            </span>
          </div>
          <p className="text-xl font-semibold text-foreground font-mono">
            <AnimatedCounter
              value={stat.value}
              duration={1200 + i * 200}
            />
          </p>
        </div>
      ))}
    </div>
  );
};

export default DatasetStats;