from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Float
from .config import config
import os

engine = create_engine(os.environ[config["dbUrl"]])
Base = declarative_base()

Session = sessionmaker(bind=engine)


class FtScores(Base):
    __tablename__ = "ft_scores"
    __table_args__ = {"schema": "main"}

    id = Column(BigInteger, primary_key=True)
    modelId = Column(String)
    timeLogged = Column(DateTime)
    signalIssued = Column(String)
    ftValue = Column(Float)
    currentPrice = Column(Float)


# create
Base.metadata.create_all(engine)
