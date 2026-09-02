# db.py
import os
from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean, Date, ForeignKey
)
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import date

DATABASE_URL = os.environ.get("DATABASE_BTV")  # your Supabase URL

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://",
                                        "postgresql+psycopg2://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Player(Base):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    position = Column(String)

class Match(Base):
    __tablename__ = "matches"
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    opponent = Column(String, nullable=False)
    goals = Column(Integer)
    goals_against = Column(Integer)
    competition = Column(String)
    location = Column(String)

class Training(Base):
    __tablename__ = "trainings"
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    location = Column(String)

class MatchPlayerStat(Base):
    __tablename__ = "match_player_stats"
    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    attended = Column(Boolean, default=False)
    goals = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    yellow = Column(Integer, default=0)
    red = Column(Integer, default=0)
    goalkeeper = Column(Boolean, default=False)
    referee = Column(Boolean, default=False)

class TrainingAttendance(Base):
    __tablename__ = "training_attendance"
    id = Column(Integer, primary_key=True)
    training_id = Column(Integer, ForeignKey("trainings.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    attended = Column(Boolean, default=True)