"""FastAPI entrypoint for the RWA Fractionalization Engine."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import documents, mint, properties, yield_distribution


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:  # noqa: BLE001 — surface startup DB issues without crashing tests
        print(f"[startup] database schema init skipped: {exc}")
    yield


app = FastAPI(
    title="RWA Fractionalization Ledger",
    description=(
        "Real-World Asset fractionalization engine with concurrent-safe minting, "
        "rental yield distribution, and AI-assisted property document onboarding."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(properties.router)
app.include_router(mint.router)
app.include_router(yield_distribution.router)
app.include_router(documents.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
