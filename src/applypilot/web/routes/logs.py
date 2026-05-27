"""Log viewer routes."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from applypilot.config import LOG_DIR

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

_MAX_BYTES = 512 * 1024


@router.get("", response_class=HTMLResponse)
async def logs_list(request: Request):
    files = _list_logs()
    return templates.TemplateResponse("logs.html", {
        "request": request, "files": files, "selected": None, "content": None,
    })


@router.get("/{filename}", response_class=HTMLResponse)
async def log_view(request: Request, filename: str):
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    log_path = LOG_DIR / filename
    if not log_path.exists() or log_path.suffix not in (".log", ".txt"):
        raise HTTPException(status_code=404, detail="Log file not found")

    size = log_path.stat().st_size
    if size > _MAX_BYTES:
        with open(log_path, "rb") as f:
            f.seek(size - _MAX_BYTES)
            content = f.read().decode("utf-8", errors="replace")
        content = f"[... showing last {_MAX_BYTES // 1024}KB ...]\n" + content
    else:
        content = log_path.read_text(encoding="utf-8", errors="replace")

    return templates.TemplateResponse("logs.html", {
        "request": request, "files": _list_logs(), "selected": filename, "content": content,
    })


def _list_logs() -> list[dict]:
    if not LOG_DIR.exists():
        return []
    return [
        {"name": p.name, "size_kb": round(p.stat().st_size / 1024, 1)}
        for p in sorted(LOG_DIR.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    ]
