"""Dashboard routes: main page + HTMX partial endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from applypilot.database import get_connection, get_stats
from applypilot.web.state import pipeline_state
from applypilot.web.templates_config import templates

router = APIRouter()


def _get_jobs(min_score: int = 5, search: str = "", show_skipped: bool = False) -> list[dict]:
    conn = get_connection()
    if show_skipped:
        where = "skipped = 1"
        params: list = []
    else:
        where = "fit_score >= ? AND (skipped IS NULL OR skipped = 0)"
        params = [min_score]
    rows = conn.execute(f"""
        SELECT url, title, salary, location, site, fit_score, score_reasoning,
               full_description, application_url, applied_at, apply_status,
               apply_error, last_attempted_at, tailored_resume_path, cover_letter_path,
               skipped
        FROM jobs
        WHERE {where}
        ORDER BY fit_score DESC NULLS LAST, discovered_at DESC
        LIMIT 300
    """, params).fetchall()
    jobs = [dict(r) for r in rows]
    if search and not show_skipped:
        sl = search.lower()
        jobs = [j for j in jobs if sl in (j.get("title") or "").lower()
                or sl in (j.get("site") or "").lower()
                or sl in (j.get("location") or "").lower()]
    return jobs


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html", {
        "stats": get_stats(), "jobs": _get_jobs(), "pipeline": pipeline_state.as_dict(),
    })


@router.get("/partials/stats", response_class=HTMLResponse)
async def stats_partial(request: Request):
    return templates.TemplateResponse(request, "partials/stats.html", {
        "stats": get_stats(),
        "pipeline": pipeline_state.as_dict(),
    })


@router.get("/partials/job-cards", response_class=HTMLResponse)
async def job_cards_partial(request: Request, min_score: int = 5, search: str = "", show_skipped: int = 0):
    skipped = bool(show_skipped)
    return templates.TemplateResponse(request, "partials/job_cards.html", {
        "jobs": _get_jobs(min_score=min_score, search=search, show_skipped=skipped),
        "show_skipped": skipped,
    })


@router.post("/jobs/skip", response_class=HTMLResponse)
async def skip_job(url: str = Form(...)):
    conn = get_connection()
    conn.execute("UPDATE jobs SET skipped = 1 WHERE url = ?", (url,))
    conn.commit()
    return HTMLResponse("")


@router.post("/jobs/unskip", response_class=HTMLResponse)
async def unskip_job(url: str = Form(...)):
    conn = get_connection()
    conn.execute("UPDATE jobs SET skipped = 0 WHERE url = ?", (url,))
    conn.commit()
    return HTMLResponse("")


@router.get("/partials/pipeline-status", response_class=HTMLResponse)
async def pipeline_status_partial(request: Request):
    return templates.TemplateResponse(request, "partials/pipeline_status.html", {
        "pipeline": pipeline_state.as_dict(),
    })
