import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")


def create_resilient_engine():
    global DATABASE_URL
    connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    try:
        eng = create_engine(DATABASE_URL, connect_args=connect_args)
        with eng.connect():
            pass
        return eng
    except Exception as exc:
        if not DATABASE_URL.startswith("sqlite"):
            print(f"\n[DATABASE NOTICE] Could not connect to configured database ({exc}).")
            print("[DATABASE NOTICE] Automatically falling back to local SQLite database: sqlite:///./app.db\n")
            DATABASE_URL = "sqlite:///./app.db"
            return create_engine("sqlite:///./app.db", connect_args={"check_same_thread": False})
        raise exc


engine = create_resilient_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)


class Base(DeclarativeBase):
    pass


def migrate_db_schema(eng):
    """Automatically upgrades existing database tables with missing columns like user_id."""
    try:
        inspector = inspect(eng)
        existing_tables = inspector.get_table_names()

        with eng.connect() as conn:
            # 1. Check learnings table for user_id
            if "learnings" in existing_tables:
                columns = [c["name"] for c in inspector.get_columns("learnings")]
                if "user_id" not in columns:
                    print("[MIGRATION] Adding missing 'user_id' column to 'learnings' table...")
                    conn.execute(text("ALTER TABLE learnings ADD COLUMN user_id INT NOT NULL DEFAULT 1"))
                    conn.commit()

            # 2. Check posts table for user_id and image_url
            if "posts" in existing_tables:
                columns = [c["name"] for c in inspector.get_columns("posts")]
                if "user_id" not in columns:
                    print("[MIGRATION] Adding missing 'user_id' column to 'posts' table...")
                    conn.execute(text("ALTER TABLE posts ADD COLUMN user_id INT NOT NULL DEFAULT 1"))
                    conn.commit()
                if "image_url" not in columns:
                    print("[MIGRATION] Adding missing 'image_url' column to 'posts' table...")
                    conn.execute(text("ALTER TABLE posts ADD COLUMN image_url VARCHAR(500) NULL"))
                    conn.commit()
    except Exception as exc:
        print(f"[MIGRATION WARNING] Automatic schema check encountered: {exc}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
