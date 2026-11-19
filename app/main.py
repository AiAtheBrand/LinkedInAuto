from pathlib import Path
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine, migrate_db_schema
from app.routers.auth import router as auth_router
from app.routers.learning import router as learning_router
from app.routers.linkedin import router as linkedin_router
from app.routers.post import router as post_router
from app.routers.publication import router as publication_router

Base.metadata.create_all(bind=engine)
migrate_db_schema(engine)

app = FastAPI(title="LinkedIn Content Automation")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "null",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(learning_router)
app.include_router(post_router)
app.include_router(linkedin_router)
app.include_router(publication_router)

# Mount uploads directory for user-uploaded media
# Mount uploads directory for user-uploaded media
project_root = Path(__file__).resolve().parent.parent

media_dir = Path(
    os.getenv("UPLOAD_DIR", str(project_root / "uploads" / "media"))
).resolve()

uploads_dir = media_dir.parent

media_dir.mkdir(parents=True, exist_ok=True)

app.mount(
    "/uploads",
    StaticFiles(directory=str(uploads_dir)),
    name="uploads"
)


# Mount frontend directory so the app can be used directly from http://127.0.0.1:8000/app/
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="frontend")


@app.get("/")
def root():
    return {
        "message": "LinkedIn Content Automation API",
        "app_ui": "http://127.0.0.1:8000/app/",
        "docs": "http://127.0.0.1:8000/docs"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
