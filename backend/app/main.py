from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import signals, companies, sync

app = FastAPI(title="xAID Signal Platform", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(signals.router, prefix="/api")
app.include_router(companies.router, prefix="/api")
app.include_router(sync.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
