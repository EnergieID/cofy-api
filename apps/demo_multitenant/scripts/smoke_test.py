"""Check a running management API end to end, logging in through the dev identity provider (`task dev-idp`).

Usage: python3 smoke_test.py [http://localhost:8080]

The API has to run on the demo's seed data, against the dev identity provider, whose users all have the password
`pwd`. Standard library only, so it runs wherever Python does.
"""

import html
import http.cookiejar
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request


def client() -> urllib.request.OpenerDirector:
    """A browser stand-in: it keeps cookies, for the API and the identity provider alike, and follows redirects."""
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def status(browser: urllib.request.OpenerDirector, url: str) -> int:
    try:
        with browser.open(url) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


def log_in(api: str, username: str) -> urllib.request.OpenerDirector:
    """Log *username* in, through the identity provider's own login form."""
    browser = client()
    with browser.open(f"{api}/auth/login") as response:
        page = response.read().decode()
        login_url = response.url
    form = re.search(r'<form[^>]*action="([^"]*)"', page)
    if form is None:
        raise AssertionError(f"No login form at {login_url}")
    fields = {
        html.unescape(name): html.unescape(value)
        for name, value in re.findall(r'<input[^>]*name="([^"]+)"[^>]*value="([^"]*)"', page)
    }
    fields |= {"Input.Username": username, "Input.Password": "pwd", "Input.Button": "login"}
    action = urllib.parse.urljoin(login_url, html.unescape(form.group(1)))
    # The identity provider sends the browser back through the API's callback, which logs it in.
    with browser.open(action, data=urllib.parse.urlencode(fields).encode()) as response:
        if not response.url.startswith(api):
            raise AssertionError(f"{username} did not get back to the API, but ended at {response.url}")
    return browser


def get_json(browser: urllib.request.OpenerDirector, url: str):
    with browser.open(url) as response:
        return json.loads(response.read())


def check(description: str, condition: bool) -> None:
    print(f"{'ok  ' if condition else 'FAIL'} {description}")
    if not condition:
        raise SystemExit(1)


def main(api: str) -> None:
    anonymous = client()
    check("the console loads", status(anonymous, f"{api}/") == 200)
    check("the API refuses anyone not logged in", status(anonymous, f"{api}/management/communities") == 401)

    admin = log_in(api, "admin")
    check("a system admin is logged in", get_json(admin, f"{api}/auth/me")["system_admin"] is True)
    slugs = [community["slug"] for community in get_json(admin, f"{api}/management/communities")]
    check(f"a system admin sees every community ({', '.join(slugs)})", {"demo", "empty"} <= set(slugs))

    nobody = log_in(api, "nobody")
    check("someone without access is logged in", status(nobody, f"{api}/auth/me") == 200)
    check("someone without access is refused the communities", status(nobody, f"{api}/management/communities") == 403)


if __name__ == "__main__":
    main(sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8080")
