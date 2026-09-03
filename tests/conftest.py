import os

os.environ.setdefault("INGEST_ON_STARTUP", "false")
os.environ.setdefault("START_SCHEDULER", "false")
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test.sqlite3")
os.environ.setdefault("REFRESH_TOKEN", "test-token")
