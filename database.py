from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

db_url = "postgresql+psycopg://simson:fyznad-peQhe0-tadfif@127.0.0.1:5432/chatDatabase"
engine = create_engine(db_url)
session = sessionmaker(autocommit=False, autoflush=False,bind= engine)
