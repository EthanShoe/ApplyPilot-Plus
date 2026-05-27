"""Dashboard routes: main page + HTMX partial endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from applypilot.database import get_connection, get_stats
from applypilot.web.state import pipeline_state
from applypilot.web.templates_config import templates

router = APIRouter()


def _get_jobs(min_score: int = 5, search: str = "") -> list[dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT url, title, salary, location, site, fit_score, score_reasoning,
               full_description, application_url, applied_at, apply_status,
               apply_error, last_attempted_at, tailored_resume_path, cover_letter_path
        FROM jobs
        WHERE fit_score >= ?
        ORDER BY fit_score DESC, discovered_at DESC
        LIMIT 300
    """, (min_score,)).fetchall()
    jobs = [dict(r) for r in rows]
    if search:
        sl = search.lower()
        jobs = [j for j in jobs if sl in (j.get("title") or "").lower()
                or sl in (j.get("site") or "").lower()
                or sl in (j.get("location") or "").lower()]
    return jobs


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    stats = get_stats()
    jobs = _get_jobs()
    pipeline = pipeline_state.as_dict()
    return templates.TemplateResponse("dashboard.html", {
        "request": request, "stats": stats, "jobs": jobs, "pipeline": pipeline,
    })


@router.get("/partials/stats", response_class=HTMLResponse)
async def stats_partial(request: Request):
    return templates.TemplateResponse("partials/stats.html", {
        "request": request,
        "stats": get_stats(),
        "pipeline": pipeline_state.as_dict(),
    })


@router.get("/partials/job-cards", response_class=HTMLResponse)
async def job_cards_partial(request: Request, min_score: int = 5, search: str = ""):
    return templates.TemplateResponse("partials/job_cards.html", {
        "request": request,
        "jobs": _get_jobs(min_score=min_score, search=search),
    })


@router.get("/partials/pipeline-status", response_class=HTMLResponse)
async def pipeline_status_partial(request: Request):
    return templates.TemplateResponse("partials/pipeline_status.html", {
        "request": request,
        "pipeline": pipeline_state.as_dict(),
    })
