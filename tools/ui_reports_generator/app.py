# Deployed by:
# uvicorn app:app --reload --host 0.0.0.0 --port 8002
from __future__ import annotations

import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.templating import Jinja2Templates
from starlette.responses import RedirectResponse

from cli import do_update_pulls
from common_all import get_logger
from github import load_branches_cache, load_metadata_cache
from gitlab import get_latest_infos_for_branch

HERE = Path(__file__).parent
log_file = HERE / "app.log"
logger = get_logger(__name__, log_file)

app = FastAPI()

templates = Jinja2Templates(directory="templates", trim_blocks=True, lstrip_blocks=True)

LAST_UPDATE_TS = 0
UPDATE_ALLOWED_EVERY_S = 30


@app.get("/branch/{branch_name:path}")
async def get_branch_info(branch_name: str):
    try:
        logger.info(f"Branch: {branch_name}")
        info = get_latest_infos_for_branch(branch_name, find_status=True)
        return {"info": info}
    except Exception as e:
        logger.exception(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/dashboard")
async def get_dashboard(request: Request):
    try:
        logger.info("get_dashboard")
        branches_info = load_branches_cache()
        metadata = load_metadata_cache()
        last_update = metadata["last_update"]
        branches_list = sorted(
            branches_info.values(),
            key=lambda branch_info: branch_info.last_commit_timestamp,
            reverse=True,
        )
        branches_with_ui = [branch for branch in branches_list if branch.job_infos]
        return templates.TemplateResponse(  # type: ignore
            "dashboard.html",
            {
                "request": request,
                "branches": branches_with_ui,
                "last_update": last_update,
            },
        )
    except Exception as e:
        logger.exception(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/update")
async def update_dashboard():
    logger.info("update_dashboard")
    try:
        global LAST_UPDATE_TS
        if time.time() - LAST_UPDATE_TS > UPDATE_ALLOWED_EVERY_S:
            do_update_pulls()
            LAST_UPDATE_TS = time.time()  # type: ignore
        else:
            time.sleep(5)
        return RedirectResponse(url="/dashboard")
    except Exception as e:
        logger.exception(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
