from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from core.config import settings
import os

# Support Postgres (production) and a local SQLite fallback for demos/tests.
if settings.database_hostname == "sqlite":
    # Use a local file-based sqlite database. Path comes from settings.database_name.
    db_path = settings.database_name or "./test.db"
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.abspath(db_path)}"
    # For SQLite, need check_same_thread=False when using with multiple threads.
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    SQLALCHEMY_DATABASE_URL = f"postgresql+psycopg2://{settings.database_username}:{settings.database_password}@{settings.database_hostname}:{settings.database_port}/{settings.database_name}"
    engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_size=10, max_overflow=20)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()