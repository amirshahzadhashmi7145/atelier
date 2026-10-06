"""Database connection.

SQLite is the development database. PostgreSQL is the production one.
Both are reached through SQLAlchemy, so the planning code talks to a
session and does not care which engine is underneath (NFR-13).

Foreign keys are off by default in SQLite. We turn them on so a deleted
project takes its requirements and tasks with it.
"""

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


def make_engine(url: str):
    kwargs: dict = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        # One in-memory database shared by every connection. Tests need this.
        if url.endswith(":memory:"):
            kwargs["poolclass"] = StaticPool
    engine = create_engine(url, **kwargs)
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def make_session_factory(engine: Engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def align_schema(engine: Engine) -> None:
    """Add columns introduced after a database file already existed.

    create_all builds missing tables. It does not alter an old table.
    """

    inspector = inspect(engine)
    if inspector.has_table("tasks"):
        names = {column["name"] for column in inspector.get_columns("tasks")}
        if "branch_name" not in names:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE tasks ADD COLUMN branch_name VARCHAR(200)"))
    if inspector.has_table("projects"):
        names = {column["name"] for column in inspector.get_columns("projects")}
        with engine.begin() as connection:
            if "github_repo" not in names:
                connection.execute(text("ALTER TABLE projects ADD COLUMN github_repo VARCHAR(200)"))
            if "paused" not in names:
                connection.execute(text("ALTER TABLE projects ADD COLUMN paused BOOLEAN DEFAULT 0"))
            if "spend_ceiling_tokens" not in names:
                connection.execute(
                    text("ALTER TABLE projects ADD COLUMN spend_ceiling_tokens INTEGER DEFAULT 1000000")
                )
