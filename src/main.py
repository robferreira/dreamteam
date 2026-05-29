from contextlib import asynccontextmanager

from src.config import ensure_plugins_path

ensure_plugins_path()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes.agents import router as agents_router
from src.api.routes.dream_teams import router as dream_teams_router
from src.api.routes.magic import router as magic_router
from src.api.routes.projects import router as projects_router
from src.api.routes.tasks import router as tasks_router
from src.logging_config import configure_logging, get_logger
from src.memory.postgres import init_db
from src.memory.rag import bootstrap_standards
from src.settings import get_settings

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    await init_db()
    await bootstrap_standards()
    logger.info("dreamteam_started", version=get_settings().app_version)
    yield
    logger.info("dreamteam_shutdown")


app = FastAPI(
    title="DreamTeam API",
    description="Multi-agent platform with runtime model selection",
    version=get_settings().app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dream_teams_router, prefix="/dream-teams", tags=["dream-teams"])
app.include_router(magic_router, prefix="/work-your-magic", tags=["work-your-magic"])
app.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
app.include_router(agents_router, prefix="/agents", tags=["agents"])
app.include_router(projects_router, prefix="/projects", tags=["projects"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": get_settings().app_version}


@app.get("/workflows")
async def list_workflows():
    from src.workflows.loader import list_workflow_names

    return {"workflows": list_workflow_names()}
