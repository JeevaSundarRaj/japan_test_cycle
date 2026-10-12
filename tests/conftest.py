import json
import os
from pathlib import Path

import pytest

CREDENTIALS_FILE = Path(__file__).resolve().parent.parent / "credentials.json"
TEST_DATA_FILE = Path(__file__).resolve().parent.parent / "test_data.json"


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    """Auto-accept mic/camera prompts with fake devices so calls can connect."""
    args = browser_type_launch_args.get("args", []) + [
        "--use-fake-ui-for-media-stream",
        "--use-fake-device-for-media-stream",
    ]
    return {**browser_type_launch_args, "args": args}


@pytest.fixture(scope="session")
def credentials():
    """Per-user credentials: {"admin_user": {"email", "password"}, ...}."""
    if CREDENTIALS_FILE.exists():
        data = json.loads(CREDENTIALS_FILE.read_text())
        return {k: v for k, v in data.items() if isinstance(v, dict)}
    return {
        "admin_user": {
            "email": os.environ["DIALPAD_EMAIL"],
            "password": os.environ["DIALPAD_PASSWORD"],
        }
    }


@pytest.fixture(scope="session")
def test_data():
    return json.loads(TEST_DATA_FILE.read_text())
