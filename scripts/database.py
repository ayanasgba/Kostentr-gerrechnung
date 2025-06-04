from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DB_URL = 'postgresql+psycopg2://postgres:postgresql@localhost:5433/kostcalc'
engine = create_engine(DB_URL)
Session = sessionmaker(bind=engine)
