import { useEffect, useState } from "react";

const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL || "http://127.0.0.1:8000";

interface PreviewResponse {
  columns: string[];
  rows: Record<string, any>[];
  error?: string;
}

const ROWS_PER_PAGE = 10;

const DataPreview = () => {
  const [columns, setColumns] = useState<string[]>([]);
  const [rows, setRows] = useState<Record<string, any>[]>([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);

  const fetchPreview = async () => {
    try {
      setLoading(true);

      const response = await fetch(`${BACKEND_URL}/preview`);
      const data: PreviewResponse = await response.json();

      if (!data.error) {
        setColumns(data.columns);
        setRows(data.rows);
        setPage(1); // reset page on new data
      }

      setLoading(false);
    } catch (error) {
      setLoading(false);
      console.error("Preview fetch failed:", error);
    }
  };

  useEffect(() => {
    fetchPreview();

    const refresh = () => fetchPreview();

    window.addEventListener("dataset-updated", refresh);

    return () => {
      window.removeEventListener("dataset-updated", refresh);
    };
  }, []);

  // ---------------------------
  // Pagination Logic
  // ---------------------------
  const totalPages = Math.ceil(rows.length / ROWS_PER_PAGE);

  const paginatedRows = rows.slice(
    (page - 1) * ROWS_PER_PAGE,
    page * ROWS_PER_PAGE
  );

  return (
    <div className="glass rounded-lg p-5 gradient-border">
      <h2 className="text-sm font-semibold text-foreground mb-3">
        Dataset Preview
      </h2>

      {loading ? (
        <div className="text-sm text-muted-foreground">
          Loading dataset preview...
        </div>
      ) : rows.length === 0 ? (
        <div className="text-sm text-muted-foreground">
          No dataset uploaded yet.
        </div>
      ) : (
        <>
          {/* TABLE */}
          <div className="rounded-md border border-border overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-max w-full text-xs">
                
                {/* Header */}
                <thead className="bg-secondary/50">
                  <tr>
                    {columns.map((col) => (
                      <th
                        key={col}
                        className="px-3 py-2 text-left font-medium text-muted-foreground uppercase tracking-wider"
                      >
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>

                {/* Body */}
                <tbody>
                  {paginatedRows.map((row, i) => (
                    <tr
                      key={i}
                      className="border-t border-border hover:bg-secondary/30 transition-colors"
                    >
                      {columns.map((col) => {
                        const val = row[col];
                        const isEmpty =
                          val === "" || val === null || val === undefined;

                        return (
                          <td
                            key={col}
                            className={`px-3 py-2 font-mono ${
                              isEmpty
                                ? "text-destructive/70 italic"
                                : "text-foreground/80"
                            }`}
                          >
                            {isEmpty ? "null" : String(val)}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>

              </table>
            </div>
          </div>

          {/* PAGINATION */}
          <div className="flex items-center justify-between mt-4 text-xs">
            
            <span className="text-muted-foreground">
              Page {page} of {totalPages}
            </span>

            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(p - 1, 1))}
                disabled={page === 1}
                className="px-3 py-1 rounded-md bg-secondary disabled:opacity-50"
              >
                Prev
              </button>

              <button
                onClick={() => setPage((p) => Math.min(p + 1, totalPages))}
                disabled={page === totalPages}
                className="px-3 py-1 rounded-md bg-secondary disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default DataPreview;