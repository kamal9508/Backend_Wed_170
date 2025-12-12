from fastapi import FastAPI
from .routes import router as org_router
from .db import get_client

app = FastAPI(title="Organization Management Service")

app.include_router(org_router)


@app.on_event("shutdown")
def shutdown_db_client():
    try:
        client = get_client()
        client.close()
    except Exception:
        pass


if __name__ == "__main__":
    import uvicorn

    # Run without the auto-reloader in production-like mode
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
