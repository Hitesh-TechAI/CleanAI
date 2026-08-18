import { useEffect, useState } from "react";

interface AnimatedCounterProps {
  value: string;
  duration?: number;
}

const AnimatedCounter = ({ value, duration = 1200 }: AnimatedCounterProps) => {
  const [display, setDisplay] = useState(value);

  useEffect(() => {
    const match = value.match(/^(-?[0-9,.]+)(.*)$/);

    if (!match) {
      setDisplay(value);
      return;
    }

    const numStr = match[1].replace(/,/g, "");
    const suffix = match[2] || "";

    const target = parseFloat(numStr);
    if (isNaN(target)) {
      setDisplay(value);
      return;
    }

    const hasComma = match[1].includes(",");
    const isFloat = numStr.includes(".");
    const decimals = isFloat ? numStr.split(".")[1]?.length || 0 : 0;

    const startTime = performance.now();
    const start = 0;

    const animate = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);

      const eased = 1 - Math.pow(1 - progress, 3); // easeOutCubic
      const current = start + (target - start) * eased;

      let formatted: string;

      if (isFloat) {
        formatted = current.toFixed(decimals);
      } else {
        const rounded = Math.round(current);
        formatted = hasComma
          ? rounded.toLocaleString()
          : String(rounded);
      }

      setDisplay(formatted + suffix);

      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };

    requestAnimationFrame(animate);
  }, [value, duration]);

  return <span>{display}</span>;
};

export default AnimatedCounter;