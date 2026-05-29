"""Dashboard routes: main page + HTMX partial endpoints."""
from __future__ import annotations

from collections import defaultdict
from typing import List

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from applypilot.database import get_connection, get_stats, skip_jobs, unskip_jobs
from applypilot.web.state import pipeline_state
from applypilot.web.templates_config import templates

router = APIRouter()


def _group_jobs(jobs: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for job in jobs:
        title = (job.get("title") or "").lower().strip()
        desc = (job.get("description") or "").strip()
        # Use last 200 chars of description as the stable grouping tail
        # (skill tags vary at the start; the company description body is at the end)
        if title and len(desc) > 50:
            key = (title, desc[-200:].lower())
        else:
            key = (title, job.get("url", ""))
        groups[key].append(job)

    result = []
    for group in groups.values():
        rep = dict(group[0])
        rep["group_urls"] = [j["url"] for j in group]
        rep["group_count"] = len(group)
        result.append(rep)
    return result


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
               description, full_description, application_url, applied_at, apply_status,
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
    return _group_jobs(jobs)


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
    skip_jobs(get_connection(), [url])
    return HTMLResponse("")


@router.post("/jobs/unskip", response_class=HTMLResponse)
async def unskip_job(url: str = Form(...)):
    unskip_jobs(get_connection(), [url])
    return HTMLResponse("")


@router.post("/jobs/skip-group", response_class=HTMLResponse)
async def skip_job_group(urls: List[str] = Form(...)):
    skip_jobs(get_connection(), urls)
    return HTMLResponse("")


@router.post("/jobs/unskip-group", response_class=HTMLResponse)
async def unskip_job_group(urls: List[str] = Form(...)):
    unskip_jobs(get_connection(), urls)
    return HTMLResponse("")


@router.get("/partials/pipeline-status", response_class=HTMLResponse)
async def pipeline_status_partial(request: Request):
    return templates.TemplateResponse(request, "partials/pipeline_status.html", {
        "pipeline": pipeline_state.as_dict(),
    })
