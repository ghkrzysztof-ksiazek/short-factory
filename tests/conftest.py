import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from short_factory.db.models import Base


@pytest.fixture()
def sqlite_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    import short_factory.analytics.collector as analytics_collector
    import short_factory.db.session as db_session
    import short_factory.research.pipeline as research_pipeline
    import short_factory.shared.jobs as shared_jobs
    import short_factory.shared.optimization as shared_optimization

    monkeypatch.setattr(db_session, "engine", engine)
    monkeypatch.setattr(db_session, "SessionLocal", session_factory)
    monkeypatch.setattr(shared_jobs, "SessionLocal", session_factory)
    monkeypatch.setattr(research_pipeline, "SessionLocal", session_factory)
    monkeypatch.setattr(analytics_collector, "SessionLocal", session_factory)
    monkeypatch.setattr(shared_optimization, "SessionLocal", session_factory)

    db = session_factory()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)
