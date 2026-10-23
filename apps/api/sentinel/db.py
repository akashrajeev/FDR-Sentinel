from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from sentinel.config import settings


class Base(DeclarativeBase):
    pass


@lru_cache
def engine():
    return create_engine(settings().database_url, pool_pre_ping=True, connect_args={'connect_timeout': 5})


def session_factory():
    return sessionmaker(engine(), expire_on_commit=False)


def get_db():
    with Session(engine(), expire_on_commit=False) as session:
        yield session
