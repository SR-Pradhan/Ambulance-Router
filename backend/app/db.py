import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Read the connection string from the environment, falling back to a local
# database for development. Hosting platforms inject DATABASE_URL, so the same
# code runs locally and deployed with no edit.
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://localhost/ambulance_router"
)

# Managed providers hand out URLs starting with postgres://, which SQLAlchemy
# dropped support for. psycopg2 needs the postgresql:// form, so normalise it
# rather than leave a confusing "Can't load plugin" error at startup.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    # A hosted database sits behind a network and closes idle connections.
    # pool_pre_ping tests a connection before handing it out, which turns a
    # silent "server closed the connection unexpectedly" into a transparent
    # reconnect. Harmless locally, essential when deployed.
    pool_pre_ping=True,
    # Free tiers cap connections tightly, and a sleeping service reconnects
    # often, so keep the pool small and recycle it regularly.
    pool_size=5,
    max_overflow=2,
    pool_recycle=300,
)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
