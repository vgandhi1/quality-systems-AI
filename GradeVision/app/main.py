from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os

from app.core.database import Base, engine
from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User, RoleEnum
from app.core.database import SessionLocal
from app.routers import auth, inspect, logs

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(inspect.router)
app.include_router(logs.router)

os.makedirs("frontend/static", exist_ok=True)
os.makedirs("frontend/templates", exist_ok=True)

if os.path.exists("frontend/static"):
    app.mount("/static", StaticFiles(directory="frontend/static"), name="static")


def create_default_admin():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin@gradevisio n.com").first()
        if not admin:
            admin = User(
                email="admin@gradevisio n.com",
                full_name="Admin User",
                hashed_password=hash_password("admin@123"),
                role=RoleEnum.ADMIN,
            )
            db.add(admin)
            db.commit()
            print("✓ Default admin user created: admin@gradevisio n.com / admin@123")
    except Exception as e:
        print(f"Error creating default admin: {e}")
    finally:
        db.close()


@app.on_event("startup")
def startup_event():
    create_default_admin()


@app.get("/")
def root():
    return FileResponse("frontend/templates/index.html")


@app.get("/login")
def login_page():
    return FileResponse("frontend/templates/login.html")


@app.get("/dashboard")
def dashboard_page():
    return FileResponse("frontend/templates/dashboard.html")


@app.get("/inspect")
def inspect_page():
    return FileResponse("frontend/templates/inspect.html")


@app.get("/health")
def health_check():
    return {"status": "ok", "project": settings.PROJECT_NAME}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.APP_HOST, port=settings.APP_PORT)
