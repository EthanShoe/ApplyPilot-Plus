"""Pipeline control routes: start stages, stop, check status."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from applypilot.web.state import pipeline_state
from applypilot.web.templates_config import templates

router = APIRouter()
log = logging.getLogger(__name__)

PIPELINE_STAGES = {"discover", "enrich", "score", "tailor", "cover", "pdf", "all", "rescore", "retailor"}


def _status_response(request: Request, status_code: int = 200):
    return templates.TemplateResponse(
        request,
        "partials/pipeline_status.html",
        {"pipeline": pipeline_state.as_dict()},
        status_code=status_code,
    )


def _run_in_thread(stage: str, min_score: int, workers: int, validation_mode: str) -> None:
    try:
        if stage == "apply":
            from applypilot.apply.launcher import main as apply_main
            apply_main(headless=True, continuous=False)
        elif stage == "rescore":
            from applypilot.scoring.scorer import run_scoring
            run_scoring(rescore=True)
        elif stage == "retailor":
            from applypilot.database import get_connection
            conn = get_connection()
            conn.execute(
                "UPDATE jobs SET tailored_resume_path=NULL, tailored_at=NULL, "
                "cover_letter_path=NULL WHERE tailored_resume_path IS NOT NULL"
            )
            conn.commit()
            from applypilot.pipeline import run_pipeline
            run_pipeline(stages=["tailor"], min_score=min_score, workers=workers,
                         validation_mode=validation_mode)
        else:
            from applypilot.pipeline import run_pipeline
            stages = [stage] if stage != "all" else None
            if stages is None:
                ordered = ["discover", "enrich", "score", "tailor", "cover", "pdf"]
                for s in ordered:
                    if pipeline_state.should_stop():
                        break
                    run_pipeline(stages=[s], min_score=min_score, workers=workers,
                                 validation_mode=validation_mode)
            else:
                run_pipeline(stages=stages, min_score=min_score, workers=workers,
                             validation_mode=validation_mode)

        status = "stopped" if pipeline_state.should_stop() else "done"
        pipeline_state.finish(status=status)
    except Exception as e:
        log.exception("Pipeline stage '%s' failed", stage)
        pipeline_state.finish(status="error", error=str(e))


@router.post("/run/{stage}", response_class=HTMLResponse)
async def run_stage(
    request: Request,
    stage: str,
    min_score: int = 7,
    workers: int = 1,
    validation: str = "normal",
):
    if stage not in PIPELINE_STAGES and stage != "apply":
        return _status_response(request, 400)

    if not pipeline_state.start(stage):
        return _status_response(request, 409)

    from applypilot.web.app import get_executor
    get_executor().submit(_run_in_thread, stage, min_score, workers, validation)
    return _status_response(request)


@router.post("/stop", response_class=HTMLResponse)
async def stop_pipeline(request: Request):
    pipeline_state.request_stop()
    return _status_response(request)


@router.get("/status", response_class=HTMLResponse)
async def pipeline_status(request: Request):
    return _status_response(request)
