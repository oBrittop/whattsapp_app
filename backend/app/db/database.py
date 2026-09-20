import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://admin:securepassword@localhost:5432/scheduling"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    Fornece uma sessao de banco de dados por requisicao.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
