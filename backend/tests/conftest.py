import os
import tempfile
from pathlib import Path

# Configure an isolated database before importing application modules.
_test_data = tempfile.TemporaryDirectory(prefix='clause-tests-')
os.environ['DATABASE_URL'] = 'sqlite:///' + str(Path(_test_data.name) / 'test.db').replace('\\', '/')
os.environ['DEMO_SEED'] = 'false'

def pytest_sessionfinish(session, exitstatus):
    from app.db import engine
    engine.dispose()
    _test_data.cleanup()
