import os
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["Config"])

@router.get("/config")
async def get_app_config():
    debug_flag = os.getenv("DEBUG_FLAG", "false").lower() in ("true", "1", "yes")
    max_batch_size_mb = int(os.getenv("MAX_BATCH_SIZE_MB", "50"))
    
    return JSONResponse({
        "debug_flag": debug_flag,
        "max_batch_size_mb": max_batch_size_mb
    })