
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Load local environment variables during development.
# On Railway, environment variables are supplied by the platform.
load_dotenv()


# --------------------------------------------------
# DATABASE CONFIGURATION
# --------------------------------------------------

ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    if ENVIRONMENT == "production":
        raise RuntimeError(
            "DATABASE_URL must be configured in production."
        )

    # Local development default
    DATABASE_URL = "sqlite:///./app.db"


# Railway MySQL URLs may use mysql://.
# Explicitly select the PyMySQL driver installed in requirements.txt.
if DATABASE_URL.startswith("mysql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "mysql://",
        "mysql+pymysql://",
        1
    )


# SQLite requires a special connection argument.
connect_args = (
    {"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {}
)


# --------------------------------------------------
# SQLALCHEMY ENGINE
# --------------------------------------------------

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)


# --------------------------------------------------
# DATABASE SESSION
# --------------------------------------------------

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)


class Base(DeclarativeBase):
    pass


# --------------------------------------------------
# DATABASE SCHEMA MIGRATION
# --------------------------------------------------

def migrate_db_schema(eng):
    """
    Adds missing columns to existing tables.
    """

    inspector = inspect(eng)
    existing_tables = inspector.get_table_names()

    with eng.begin() as conn:

        # Update learnings table
        if "learnings" in existing_tables:
            columns = {
                column["name"]
                for column in inspector.get_columns("learnings")
            }

            if "user_id" not in columns:
                print(
                    "[MIGRATION] Adding user_id to learnings table..."
                )

                conn.execute(
                    text(
                        "ALTER TABLE learnings "
                        "ADD COLUMN user_id INT NOT NULL DEFAULT 1"
                    )
                )

        # Update posts table
        if "posts" in existing_tables:
            columns = {
                column["name"]
                for column in inspector.get_columns("posts")
            }

            if "user_id" not in columns:
                print(
                    "[MIGRATION] Adding user_id to posts table..."
                )

                conn.execute(
                    text(
                        "ALTER TABLE posts "
                        "ADD COLUMN user_id INT NOT NULL DEFAULT 1"
                    )
                )

            if "image_url" not in columns:
                print(
                    "[MIGRATION] Adding image_url to posts table..."
                )

                conn.execute(
                    text(
                        "ALTER TABLE posts "
                        "ADD COLUMN image_url VARCHAR(500) NULL"
                    )
                )


# --------------------------------------------------
# DATABASE DEPENDENCY
# --------------------------------------------------

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
