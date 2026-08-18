import { Upload, FileText } from "lucide-react";
import { useRef, useState } from "react";

const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL || "http://127.0.0.1:8000";

const FileUpload = () => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [fileName, setFileName] = useState<string | null>(null);
  const [rowCount, setRowCount] = useState<number | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const handleClick = () => {
    if (!isUploading) {
      fileInputRef.current?.click();
    }
  };

  const handleUpload = async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);

    try {
      setIsUploading(true);

      const response = await fetch(`${BACKEND_URL}/upload`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (data.rows) {
        setFileName(file.name);
        setRowCount(data.rows);

        // 🔥 Notify other components to refresh
        window.dispatchEvent(new Event("dataset-updated"));
      }

    } catch (error) {
      console.error("Upload failed:", error);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div id="upload-section" className="glass rounded-lg p-5 gradient-border">
      <h2 className="text-sm font-semibold text-foreground mb-3">
        Upload Dataset
      </h2>

      <input
        type="file"
        accept=".csv"
        ref={fileInputRef}
        className="hidden"
        onChange={(e) => {
          if (e.target.files) {
            handleUpload(e.target.files[0]);
          }
        }}
      />

      <div
        onClick={handleClick}
        className={`border-2 border-dashed border-border rounded-lg p-8 text-center transition-colors cursor-pointer group ${
          isUploading ? "opacity-50 cursor-not-allowed" : "hover:border-primary/50"
        }`}
      >
        <Upload className="w-8 h-8 text-muted-foreground mx-auto mb-3 group-hover:text-primary transition-colors" />
        <p className="text-sm text-muted-foreground">
          Drag & drop your{" "}
          <span className="text-primary font-medium">CSV file</span> here
        </p>
        <p className="text-xs text-muted-foreground mt-1">
          {isUploading ? "Uploading..." : "or click to browse"}
        </p>
      </div>

      {fileName && rowCount !== null && (
        <div className="mt-3 flex items-center gap-2 text-xs">
          <span className="inline-block w-2 h-2 rounded-full bg-green-500" />
          <FileText className="w-3.5 h-3.5 text-muted-foreground" />
          <span className="text-foreground/80 font-medium">
            {fileName}
          </span>
          <span className="text-muted-foreground">
            — {rowCount.toLocaleString()} rows
          </span>
        </div>
      )}
    </div>
  );
};

export default FileUpload;