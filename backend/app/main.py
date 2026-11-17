from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import router as api_router
from app.core.config import settings
from app.services.llm import create_http_client, set_http_client


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    client = create_http_client()
    set_http_client(client)
    try:
        yield
    finally:
        set_http_client(None)
        await client.aclose()


app = FastAPI(title="DnD Master API", version="0.1.0", lifespan=lifespan)

if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.middleware("http")
async def reject_foreign_origins(request: Request, call_next):
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if origin is not None:
            allowed = set(settings.cors_origin_list)
            host = request.headers.get("host")
            same_origin = bool(host) and origin in {
                f"{request.url.scheme}://{host}",
                f"http://{host}",
                f"https://{host}",
            }
            if origin not in allowed and not same_origin:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Запрос с недопустимого origin"},
                )
    return await call_next(request)


app.include_router(api_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
