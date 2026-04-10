# database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
import os

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://neondb_owner:npg_z7nBJOCva3Mt@ep-young-snow-amadr6pe-pooler.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

Base = declarative_base()
Base.query = db_session.query_property()

def init_db():
    # Import models here to avoid circular imports
    from models import User, Module, ModuleEnrollment, Quiz, Attempt
    Base.metadata.create_all(bind=engine)
