from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routes.config import router as config_router
from app.routes.recordings import router as recordings_router


from services.gdrive_service import ensure_google_authenticated

# ============================================================
# PROJECT DIRECTORIES
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# ============================================================
# FASTAPI LIFESPAN (STARTUP / SHUTDOWN EVENTS)
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs automatically on application startup
    ensure_google_authenticated()
    yield
    # Cleanup tasks on shutdown (if any) go here

# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="Screen & Audio Share",
    version="1.0.0",
    description="Screen sharing, audio sharing, and recording platform",
    lifespan=lifespan,
)

# ============================================================
# STATIC FILES
# ============================================================

app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static",
)

# ============================================================
# JINJA2 TEMPLATES
# ============================================================

templates = Jinja2Templates(
    directory=str(TEMPLATES_DIR),
)

# ============================================================
# FRONTEND ROUTES
# ============================================================

@app.get("/", name="home")
async def index(request: Request):
    """
    Render the main screen and audio sharing page.
    """
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
        },
    )

# ============================================================
# API ROUTES
# ============================================================

app.include_router(
    recordings_router,
    prefix="/api",
)

app.include_router(config_router, prefix="/api")
# ============================================================
# APPLICATION ENTRY POINT
# ============================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
