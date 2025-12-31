from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.server.api.blueprints import router as blueprints_router
from app.server.api.files import router as files_router
from app.server.api.templates import router as templates_router
from app.server.api.yaml import router as yaml_router
from app.server.logger import logger

# Initialize FastAPI app
app = FastAPI(
    title="ReportFlow Studio API",
    description="AI-First Report Generation Platform",
    version="3.0.0",
)

# Include Routers
app.include_router(templates_router)
app.include_router(blueprints_router)
app.include_router(files_router)
app.include_router(yaml_router)


# CORS Configuration
origins = [
    "http://localhost:5173",  # Vite default
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    logger.info("Application startup: ReportFlow Studio API")


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "3.0.0"}
