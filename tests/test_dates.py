"""The demo follows the real calendar: the data is built around whatever day it runs."""
import os, subprocess, sys, tempfile, sqlite3, pytest
from conftest import Client

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def test_today_is_the_pinned_day():
    assert Client("modir").get("/manager/overview").json()["today"] == "3 آبان 1405"

@pytest.mark.parametrize("day,jalali", [("2026-10-25", "1405/08/03"), ("2026-12-21", "1405/09/30"), ("2026-09-26", "1405/07/04")])
def test_seed_works_on_any_day(day, jalali):
    path = os.path.join(tempfile.mkdtemp(), "s.db")
    out = subprocess.run([sys.executable, "seed.py"], cwd=ROOT, capture_output=True, text=True,
                         env={**os.environ, "DB_PATH": path, "DEMO_TODAY": day})
    assert out.returncode == 0, out.stderr
    assert jalali in out.stdout
    c = sqlite3.connect(path)
    assert c.execute("SELECT COUNT(*) FROM student_attendance WHERE date = ?", (day,)).fetchone()[0] == 30
    assert c.execute("SELECT MAX(date) FROM assessments").fetchone()[0] <= day
    deadlines = [r[0] for r in c.execute("SELECT deadline FROM letters WHERE status = 'new' AND deadline IS NOT NULL")]
    assert deadlines and all(d >= day for d in deadlines)   # open letters are due after "today"
