# app/main.py
from fastapi import FastAPI
from app.api.router import router as api_router
from app.db import models
from app.db.database import engine
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Project Management API", version="0.1.0")

# CORS for React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include your API router
app.include_router(api_router, prefix="/api")

# ✅ Create all tables
models.Base.metadata.create_all(bind=engine)

@app.get("/health")
def health():
    return {"status": "ok"}
