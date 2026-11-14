"""Database Engine, Session Factory, and Base declarative model."""
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

# SQLite connection args for multithreaded fast access
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def sync_db_schema(db_engine):
    """Ensures SQLite tables have all columns defined in ORM models."""
    from sqlalchemy import text, inspect
    inspector = inspect(db_engine)
    if "sqlite" not in str(db_engine.url):
        return

    for table_name, table in Base.metadata.tables.items():
        if inspector.has_table(table_name):
            existing_cols = {col["name"] for col in inspector.get_columns(table_name)}
            with db_engine.begin() as conn:
                for col in table.columns:
                    if col.name not in existing_cols:
                        col_type = col.type.compile(db_engine.dialect)
                        nullable = "NULL" if col.nullable else "DEFAULT ''"
                        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type}"))


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for yielding transactional database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
