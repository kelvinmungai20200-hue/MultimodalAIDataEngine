from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api import ingest  # noqa: E402

app = FastAPI(title="Multimodal AI Data Engine",
              description="Ingest and management APIs for multimodal datasets",
              version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router)


@app.get("/health")
def health():
    return {"status": "ok"}


# Optional Prometheus metrics endpoint — only registered when prometheus_client is available
try:
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST  # type: ignore
    from fastapi.responses import Response

    @app.get("/metrics")
    def metrics():
        # generate_latest uses the default REGISTRY which includes any Counters created elsewhere
        data = generate_latest()
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)
except Exception:
    # prometheus_client not installed — skip metrics endpoint
    pass
