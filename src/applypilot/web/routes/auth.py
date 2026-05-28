"""Authentication routes: login and logout."""
from __future__ import annotations

import os

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from applypilot.web.templates_config import templates

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    if _is_authed(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login")
async def login_post(request: Request):
    form = await request.form()
    submitted = form.get("password", "")
    expected = os.environ.get("UI_PASSWORD", "")

    if submitted == expected:
        request.session["authed"] = True
        return RedirectResponse("/", status_code=302)

    return templates.TemplateResponse(request, "login.html", {"error": "Incorrect password."})


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=302)


def _is_authed(request: Request) -> bool:
    return not os.environ.get("UI_PASSWORD") or bool(request.session.get("authed"))
