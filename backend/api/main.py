import hmac
import json
import os
import threading
import uuid
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from engine import loaders
from engine.history import History, HistoryError
from engine.ops import OpError
from engine.profiler import compare, profile, suggest

MAX_SESSIONS = 5


def auth(x_cleanai_token: Optional[str] = Header(default=None)):
    """If CLEANAI_TOKEN is set (Electron sets it at launch), every request must send it."""
    token = os.environ.get("CLEANAI_TOKEN")
    if token and not hmac.compare_digest((x_cleanai_token or "").encode(), token.encode()):
        raise HTTPException(401, "Unauthorized.")


app = FastAPI(title="CleanAI", dependencies=[Depends(auth)])
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # dev UI only
    allow_methods=["*"],
    allow_headers=["*"],
)


class Session:
    def __init__(self, history: History, filename: str):
        self.history = history
        self.filename = filename
        self.lock = threading.RLock()


_sessions: dict[str, Session] = {}
_registry_lock = threading.Lock()


def _get(sid: str) -> Session:
    s = _sessions.get(sid)
    if s is None:
        raise HTTPException(404, "Session not found.")
    return s


def _state(s: Session) -> dict:
    h = s.history
    return {"rows": len(h.df), "cols": h.df.shape[1],
            "can_undo": h.can_undo, "can_redo": h.can_redo, "steps": h.steps()}


def _check_capacity():
    if len(_sessions) >= MAX_SESSIONS:
        raise HTTPException(429, f"Too many open datasets (max {MAX_SESSIONS}). Close one first.")


# ---------- request models ----------
class SheetsRequest(BaseModel):
    path: str


class LoadRequest(BaseModel):
    path: str
    sheet: Optional[str] = None
    all_text: bool = False


class ApplyRequest(BaseModel):
    op: dict


class ExportRequest(BaseModel):
    path: str


# ---------- endpoints ----------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/sheets")
def sheets(req: SheetsRequest):
    try:
        return {"sheets": loaders.list_sheets(req.path)}
    except loaders.LoadError as e:
        raise HTTPException(400, str(e))


@app.post("/load")
def load_file(req: LoadRequest):
    with _registry_lock:
        _check_capacity()
    try:
        df = loaders.load(req.path, sheet=req.sheet, all_text=req.all_text)
    except loaders.LoadError as e:
        raise HTTPException(400, str(e))
    sid = uuid.uuid4().hex
    s = Session(History(df), os.path.basename(req.path))
    with _registry_lock:
        _check_capacity()
        _sessions[sid] = s
    return {"session_id": sid, "filename": s.filename, "state": _state(s)}


@app.delete("/sessions/{sid}")
def close_session(sid: str):
    with _registry_lock:
        if _sessions.pop(sid, None) is None:
            raise HTTPException(404, "Session not found.")
    return {"closed": True}


@app.get("/sessions/{sid}/state")
def state(sid: str):
    s = _get(sid)
    with s.lock:
        return _state(s)


@app.get("/sessions/{sid}/profile")
def get_profile(sid: str):
    s = _get(sid)
    with s.lock:
        return profile(s.history.df)


@app.get("/sessions/{sid}/suggestions")
def get_suggestions(sid: str):
    s = _get(sid)
    with s.lock:
        return {"suggestions": suggest(s.history.df)}


@app.get("/sessions/{sid}/preview")
def preview(sid: str, offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
    s = _get(sid)
    with s.lock:
        df = s.history.df
        chunk = df.iloc[offset: offset + limit]
        data = json.loads(chunk.to_json(orient="split", date_format="iso"))
        return {"columns": data["columns"], "rows": data["data"],
                "offset": offset, "total_rows": len(df)}


@app.post("/sessions/{sid}/apply")
def apply_op(sid: str, req: ApplyRequest):
    s = _get(sid)
    with s.lock:
        try:
            result = s.history.apply(req.op)
        except OpError as e:
            raise HTTPException(400, str(e))
        return {"result": result.model_dump(), "state": _state(s)}


@app.post("/sessions/{sid}/undo")
def undo(sid: str):
    s = _get(sid)
    with s.lock:
        try:
            s.history.undo()
        except HistoryError as e:
            raise HTTPException(409, str(e))
        return _state(s)


@app.post("/sessions/{sid}/redo")
def redo(sid: str):
    s = _get(sid)
    with s.lock:
        try:
            s.history.redo()
        except HistoryError as e:
            raise HTTPException(409, str(e))
        except OpError as e:
            raise HTTPException(400, str(e))
        return _state(s)


@app.post("/sessions/{sid}/reset")
def reset(sid: str):
    s = _get(sid)
    with s.lock:
        s.history.reset()
        return _state(s)


@app.get("/sessions/{sid}/compare")
def get_compare(sid: str):
    s = _get(sid)
    with s.lock:
        return compare(s.history.original, s.history.df)


@app.post("/sessions/{sid}/export")
def export_file(sid: str, req: ExportRequest):
    s = _get(sid)
    with s.lock:
        try:
            loaders.export(s.history.df, req.path)
        except loaders.ExportError as e:
            raise HTTPException(400, str(e))
        return {"path": req.path, "rows": len(s.history.df)}