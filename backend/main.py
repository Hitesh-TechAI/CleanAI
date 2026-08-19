from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import pandas as pd
import io

from ai.orchestrator import run_orchestrator

app = FastAPI()

# ---- CORS ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://192.168.43.185:8080",
        "https://clean-ai-seven.vercel.app",
        "https://clean-edygsf80y-hitesh-37f5.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ---- In-memory datastore (single user for now) ----
DATASTORE = {
    "df": None
}

# ---- Request Schema ----
class ChatRequest(BaseModel):
    message: str


# ---- Routes ----

@app.get("/")
def root():
    return {"message": "CleanAI Backend Running"}


@app.post("/upload")
async def upload_dataset(file: UploadFile = File(...)):
    contents = await file.read()

    try:
        df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
    except Exception as e:
        return {"error": f"Invalid CSV file: {str(e)}"}

    DATASTORE["df"] = df

    return {
        "rows": len(df),
        "columns": list(df.columns)
    }

@app.get("/preview")
def preview_dataset():

    df = DATASTORE["df"]

    if df is None:
        return {"columns": [], "rows": []}

    # Copy full dataframe
    preview_df = df.copy()

    # Convert ALL NaN/NaT to None for JSON compatibility
    preview_df = preview_df.astype(object).where(pd.notnull(preview_df), None)

    return {
        "columns": list(preview_df.columns),
        "rows": preview_df.to_dict(orient="records"),
    }
@app.post("/chat")
async def chat(request: ChatRequest):
    df = DATASTORE["df"]

    if df is None:
        return {"error": "No dataset uploaded."}

    if "session_state" not in DATASTORE:
        DATASTORE["session_state"] = {}

    updated_df, response = run_orchestrator(
        df,
        request.message,
        DATASTORE["session_state"]
    )
    # Only update dataset if a new dataframe is returned
    if updated_df is not None:
        DATASTORE["df"] = updated_df

    return response


@app.get("/download")
def download_dataset():
    df = DATASTORE["df"]

    if df is None:
        return {"error": "No dataset available"}

    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    return StreamingResponse(
        iter([csv_buffer.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=cleaned_dataset.csv"
        },
    )

@app.get("/stats")
def dataset_stats():
    df = DATASTORE["df"]

    if df is None:
        return {
            "rows": 0,
            "columns": 0,
            "missing_percent": 0,
            "duplicates": 0,
        }

    total_rows = int(df.shape[0])
    total_columns = int(df.shape[1])

    if total_rows == 0 or total_columns == 0:
        missing_percent = 0
    else:
        total_cells = total_rows * total_columns
        missing_count = int(df.isnull().sum().sum())
        missing_percent = round((missing_count / total_cells) * 100, 2)

    duplicates = int(df.duplicated().sum())

    return {
        "rows": total_rows,
        "columns": total_columns,
        "missing_percent": float(missing_percent),
        "duplicates": duplicates,
    }
