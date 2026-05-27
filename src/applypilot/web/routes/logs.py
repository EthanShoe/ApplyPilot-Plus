"""Log viewer routes."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from applypilot.config import LOG_DIR
from applypilot.web.templates_config import templates

router = APIRouter()

_MAX_BYTES = 512 * 1024


def _list_logs() -> list[str]:
    if not LOG_DIR.exists():
        return []
    return [
        p.name
        for p in sorted(LOG_DIR.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    ]


@router.get("", response_class=HTMLResponse)
async def logs_list(request: Request):
    return templates.TemplateResponse(request, "logs.html", {
        "log_files": _list_logs(), "selected": None, "content": None, "truncated": False,
    })


@router.get("/{filename}", response_class=HTMLResponse)
async def log_view(request: Request, filename: str):
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    log_path = LOG_DIR / filename
    if not log_path.exists() or log_path.suffix not in (".log", ".txt"):
        raise HTTPException(status_code=404, detail="Log file not found")

    size = log_path.stat().st_size
    truncated = size > _MAX_BYTES
    if truncated:
        with open(log_path, "rb") as f:
            f.seek(size - _MAX_BYTES)
            content = f.read().decode("utf-8", errors="replace")
        content = f"[... showing last {_MAX_BYTES // 1024}KB ...]\n" + content
    else:
        content = log_path.read_text(encoding="utf-8", errors="replace")

    return templates.TemplateResponse(request, "logs.html", {
        "log_files": _list_logs(), "selected": filename,
        "content": content, "truncated": truncated,
    })
