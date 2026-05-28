"""FastAPI application factory for ApplyPilot web UI."""
from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

log = logging.getLogger(__name__)

_executor: ThreadPoolExecutor | None = None


def get_executor() -> ThreadPoolExecutor:
    assert _executor is not None, "Executor not initialized"
    return _executor


def require_auth(request: Request):
    password = os.environ.get("UI_PASSWORD", "")
    if not password:
        return
    if not request.session.get("authed"):
        return RedirectResponse("/login", status_code=302)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _executor
    from applypilot.config import load_env, ensure_dirs
    from applypilot.database import init_db
    load_env()
    ensure_dirs()
    init_db()
    _executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="pipeline")
    log.info("ApplyPilot web UI started")
    yield
    _executor.shutdown(wait=False)
    log.info("ApplyPilot web UI stopped")


def create_app() -> FastAPI:
    app = FastAPI(title="ApplyPilot", lifespan=lifespan)

    secret = os.environ.get("UI_SECRET") or os.environ.get("UI_PASSWORD") or "applypilot-default-secret"
    app.add_middleware(
        SessionMiddleware,
        secret_key=secret,
        max_age=30 * 24 * 3600,
        https_only=False,
        same_site="lax",
    )

    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(exist_ok=True)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    auth_deps = [Depends(require_auth)]

    from applypilot.web.routes.auth import router as auth_router
    from applypilot.web.routes.dashboard import router as dashboard_router
    from applypilot.web.routes.pipeline import router as pipeline_router
    from applypilot.web.routes.settings import router as settings_router
    from applypilot.web.routes.logs import router as logs_router

    app.include_router(auth_router)
    app.include_router(dashboard_router, dependencies=auth_deps)
    app.include_router(pipeline_router, prefix="/pipeline", dependencies=auth_deps)
    app.include_router(settings_router, prefix="/settings", dependencies=auth_deps)
    app.include_router(logs_router, prefix="/logs", dependencies=auth_deps)

    return app


app = create_app()
