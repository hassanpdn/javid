"""Shared setup: one app with a fresh demo database and a fake model, for the whole test run.
Run from the repo root with: pytest"""
import sqlite3, pytest, httpx
import serve, fake_llm

PROC, BASE, DB_PATH = None, None, None

def pytest_sessionstart(session):
    global PROC, BASE, DB_PATH
    PROC, BASE, DB_PATH = serve.start()

def pytest_sessionfinish(session, exitstatus):
    if PROC:
        PROC.terminate()

_tokens = {}
def login(username, fresh=False):
    if fresh or username not in _tokens:
        r = httpx.post(BASE + "/login", json={"username": username, "password": "1234"})
        assert r.status_code == 200, r.text
        _tokens[username] = r.json()["token"]
    return _tokens[username]

class Client:
    """Calls the API as one logged-in user: Client("vali").get("/parent/child")"""
    def __init__(self, username=None, token=None):
        self.headers = {"Authorization": f"Bearer {token or (login(username) if username else '')}"}
    def get(self, path):
        return httpx.get(BASE + path, headers=self.headers, timeout=30)
    def post(self, path, json=None):
        return httpx.post(BASE + path, headers=self.headers, json={} if json is None else json, timeout=30)

def db():
    """Direct access to the test database, to set up a scenario or check what was stored."""
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def add_letter(subject, body):
    with db() as c:
        c.execute("""INSERT INTO letters (received_date, jreceived, sender, subject, body, status)
                     VALUES ('2026-10-25', '1405/08/03', 'آزمون', ?, ?, 'new')""", (subject, body))

def run_agent(username="edari"):
    """Let the letter agent work through the queue, like the staff page does."""
    c = Client(username)
    for _ in range(50):
        r = c.post("/staff/agent/next")
        if r.status_code != 200 or r.json().get("done"):
            return r

@pytest.fixture(autouse=True)
def model_behaves():
    """Every test starts with a well-behaved model; tests that need a bad one set fake_llm.MODE themselves."""
    fake_llm.MODE = "good"
    fake_llm.CALLS.clear()
    yield
    fake_llm.MODE = "good"
