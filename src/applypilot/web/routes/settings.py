"""Settings routes: profile editor, searches YAML editor, .env editor."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from applypilot.config import ENV_PATH, PROFILE_PATH, SEARCH_CONFIG_PATH

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

_SENSITIVE_KEYS = frozenset({
    "GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
    "LLM_API_KEY", "CAPSOLVER_API_KEY",
})
_MASK = "••••••••••••"

_ARRAY_FIELDS = frozenset({
    "programming_languages", "languages", "frameworks", "devops",
    "databases", "tools", "preserved_companies", "preserved_projects",
    "real_metrics",
})


def _load_profile() -> dict:
    if not PROFILE_PATH.exists():
        return {}
    try:
        return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _load_env_vars() -> list[tuple[str, str, bool]]:
    if not ENV_PATH.exists():
        return []
    results = []
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        is_sensitive = key in _SENSITIVE_KEYS
        results.append((key, _MASK if is_sensitive else val, is_sensitive))
    return results


# --- Profile ---

@router.get("/profile", response_class=HTMLResponse)
async def profile_get(request: Request):
    return templates.TemplateResponse("settings/profile.html", {
        "request": request, "profile": _load_profile(), "saved": False, "error": None,
    })


@router.post("/profile", response_class=HTMLResponse)
async def profile_post(request: Request):
    form = await request.form()
    existing = _load_profile()

    profile: dict[str, Any] = {}
    for key, val in form.items():
        parts = key.split(".", 1)
        if len(parts) == 2:
            section, field = parts
            profile.setdefault(section, {})[field] = val
        else:
            profile[key] = val

    # Convert array fields from comma-separated strings to lists
    for section in profile.values():
        if not isinstance(section, dict):
            continue
        for field, val in section.items():
            if field in _ARRAY_FIELDS and isinstance(val, str):
                section[field] = [s.strip() for s in val.split(",") if s.strip()]

    # Never overwrite password with empty string
    submitted_pw = profile.get("personal", {}).get("password", "")
    if not submitted_pw:
        existing_pw = existing.get("personal", {}).get("password", "")
        if existing_pw:
            profile.setdefault("personal", {})["password"] = existing_pw

    error = None
    try:
        PROFILE_PATH.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as e:
        error = str(e)

    return templates.TemplateResponse("settings/profile.html", {
        "request": request, "profile": profile, "saved": error is None, "error": error,
    })


# --- Searches ---

@router.get("/searches", response_class=HTMLResponse)
async def searches_get(request: Request):
    content = SEARCH_CONFIG_PATH.read_text(encoding="utf-8") if SEARCH_CONFIG_PATH.exists() else ""
    return templates.TemplateResponse("settings/searches.html", {
        "request": request, "content": content, "saved": False, "parse_error": None, "error": None,
    })


@router.post("/searches", response_class=HTMLResponse)
async def searches_post(request: Request, content: str = Form(...)):
    parse_error = error = None
    saved = False
    try:
        yaml.safe_load(content)
    except yaml.YAMLError as e:
        parse_error = str(e)
    if not parse_error:
        try:
            SEARCH_CONFIG_PATH.write_text(content, encoding="utf-8")
            saved = True
        except OSError as e:
            error = str(e)
    return templates.TemplateResponse("settings/searches.html", {
        "request": request, "content": content, "saved": saved,
        "parse_error": parse_error, "error": error,
    })


# --- Environment variables ---

@router.get("/env", response_class=HTMLResponse)
async def env_get(request: Request):
    return templates.TemplateResponse("settings/env.html", {
        "request": request, "env_vars": _load_env_vars(), "saved": False, "error": None,
    })


@router.post("/env", response_class=HTMLResponse)
async def env_post(request: Request):
    form = await request.form()
    existing: dict[str, str] = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            existing[k.strip()] = v

    keys = form.getlist("keys[]")
    values = form.getlist("values[]")

    lines = ["# ApplyPilot configuration", ""]
    for k, v in zip(keys, values):
        k = k.strip()
        if not k:
            continue
        if v == _MASK and k in existing:
            v = existing[k]
        lines.append(f"{k}={v}")

    error = None
    try:
        ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        from applypilot.config import load_env
        load_env()
    except OSError as e:
        error = str(e)

    return templates.TemplateResponse("settings/env.html", {
        "request": request, "env_vars": _load_env_vars(), "saved": error is None, "error": error,
    })
