from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from .database import engine, SessionLocal, Base
from . import models  # ensure all models are imported/registered
from .routers import ai, auth, users, properties, leases, payments, maintenance, documents, notifications, vendors

# Rate limiter — keyed by IP address
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-create ensures all tables exist (safety net alongside Alembic)
    Base.metadata.create_all(bind=engine)
    # Seed demo data if DB is empty
    from .seed import seed_db
    db = SessionLocal()
    try:
        seed_db(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="QuantumQuestProperties API",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)
app.include_router(properties.router, prefix=API_PREFIX)
app.include_router(leases.router, prefix=API_PREFIX)
app.include_router(payments.router, prefix=API_PREFIX)
app.include_router(maintenance.router, prefix=API_PREFIX)
app.include_router(documents.router, prefix=API_PREFIX)
app.include_router(notifications.router, prefix=API_PREFIX)
app.include_router(ai.router, prefix=API_PREFIX)
app.include_router(vendors.router, prefix=API_PREFIX)


@app.get("/")
def root():
    return {"message": "QuantumQuestProperties API", "version": "1.0.0", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}
