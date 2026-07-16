from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import generation, templates

app = FastAPI(title="Hairstyle MVP API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(templates.router)
app.include_router(generation.router)


@app.get("/")
async def root():
    return {"status": "ok"}
