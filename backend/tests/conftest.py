import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("FERNET_KEY", "Sf_vuPtM1moUXNhXegejlrVhtw5l3-RdsuCupG5y4go=")
os.environ.setdefault("TAVILY_API_KEY", "")  # keep tests offline: force the DuckDuckGo path unless a test opts in

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import get_current_user
from app.db import Base, get_db
from app.main import app
from app.models import User


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    yield session
    session.close()
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def user(db_session):
    u = User(email="reviewer@example.com", name="Reviewer", provider="google")
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)

    def override_get_current_user():
        return db_session.get(User, u.id)

    app.dependency_overrides[get_current_user] = override_get_current_user
    yield u
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture()
def client(db_session):
    return TestClient(app)
