"""Every /api route is guarded (F-217). Synthetic accounts only."""

import re

from tests.test_api import HEADERS, data_dir, make_client, scripts, sign_in  # noqa: F401

OPEN = {
    ("POST", "/api/auth/google"),
    ("POST", "/api/auth/dev"),
    ("POST", "/api/auth/logout"),
    ("POST", "/api/clubs/requests"),  # J-25: a stranger asks for a club; proven by Google, no session, no data
}


def test_every_route_is_guarded(data_dir, scripts) -> None:  # noqa: F811
    with make_client(data_dir, scripts) as c:
        routes = [
            (m, r.path)
            for r in c.app.routes
            if getattr(r, "path", "").startswith("/api") and "docs" not in r.path and "openapi" not in r.path
            for m in sorted(r.methods - {"HEAD", "OPTIONS"})
        ]
        assert len(routes) > 20

        def hit(method: str, path: str) -> int:
            url = re.sub(r"\{[^}]+\}", "x", path)
            kw = {} if method == "GET" else {"headers": HEADERS, "json": {}}
            return c.request(method, url, **kw).status_code

        signed_out = [(m, p, hit(m, p)) for m, p in routes if (m, p) not in OPEN]
        assert [x for x in signed_out if x[2] != 401] == []

        sign_in(c, "ta03@aub.edu.lb")  # the read-only adviser
        changing = [(m, p, hit(m, p)) for m, p in routes if m != "GET" and (m, p) not in OPEN]
        assert [x for x in changing if x[2] not in (403, 501)] == []
