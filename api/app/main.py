"""The web process.

`create_app` is a function so tests can hand in an in-memory database
and a scripted model. Importing this module also builds the real app
the server runs.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import Settings
from app.db import Base, align_schema, make_engine, make_session_factory
from app.errors import DomainError
from app.gateway import build_llm
from app.gateway.base import LlmClient
from app.routes.projects import router


def create_app(
    settings: Settings | None = None,
    llm: LlmClient | None = None,
    database_url: str | None = None,
) -> FastAPI:
    settings = settings or Settings()
    if database_url is not None:
        settings = settings.model_copy(update={"database_url": database_url})

    engine = make_engine(settings.database_url)
    Base.metadata.create_all(engine)
    align_schema(engine)

    app = FastAPI(title="Atelier", version="0.1.0")
    app.state.settings = settings
    app.state.llm = llm or build_llm(settings)
    app.state.session_factory = make_session_factory(engine)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(DomainError)
    async def domain_error(_request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    app.include_router(router)
    return app


app = create_app()
