import json
import os
from pathlib import Path

import pytest

CREDENTIALS_FILE = Path(__file__).resolve().parent.parent / "credentials.json"


@pytest.fixture(scope="session")
def credentials():
    if CREDENTIALS_FILE.exists():
        data = json.loads(CREDENTIALS_FILE.read_text())
        return data["email"], data["password"]
    return os.environ["DIALPAD_EMAIL"], os.environ["DIALPAD_PASSWORD"]
