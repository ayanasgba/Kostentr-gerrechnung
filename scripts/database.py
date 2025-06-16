from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

DB_URL = 'postgresql+psycopg2://postgres:postgresql@localhost:5433/kostcalc'
engine = create_engine(DB_URL, echo=True)

Session = scoped_session(sessionmaker(bind=engine))