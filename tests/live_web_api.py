"""C-13 browser fixture: a real HTTP/SQLite app with a scripted model and temporary synthetic data.

Only launched explicitly by web/playwright.live.config.ts. Never included in the deployment image.
"""

import tempfile
from pathlib import Path

from fastapi import FastAPI
from scripts.load_rulebook import load

from clubops.api.app import ApiConfig, create_app
from clubops.api.security import MemberStore
from clubops.contracts.common import Role
from tests.test_api import NOW, PLAN, Scripts


def build() -> FastAPI:
    output = Path("output")
    output.mkdir(exist_ok=True)
    data_dir = Path(tempfile.mkdtemp(prefix="live-web-api-", dir=output)).resolve()
    load(data_dir, None)
    members = MemberStore(data_dir)
    members.add("running-club", "Synthetic President", "president@example.com", Role.PRESIDENT)
    members.close()
    scripts = Scripts()
    scripts.queue = [PLAN for _ in range(4)]
    return create_app(
        ApiConfig(data_dir, "synthetic-browser-secret", dev_login=True, cookie_secure=False),
        scripts.factory(),
        clock=lambda: NOW,
    )
