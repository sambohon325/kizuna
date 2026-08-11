import os

os.environ.setdefault("KIZUNA_DATABASE_URL", "sqlite:///./test_anime_studio.db")

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def leave_consistent_schema_after_suite():
    yield
    # Alembic's revision marker is not part of Base.metadata and remains after
    # test cleanup, so leave the application tables consistent with that marker.
    Base.metadata.create_all(bind=engine)


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)
