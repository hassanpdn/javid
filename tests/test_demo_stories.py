"""The stories the demo is built around must show up on any day of the school year, not only on the test date.
Each date gets its own fresh database in a separate process (seed.py and db.py read their settings on import)."""
import json, os, subprocess, sys, tempfile
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# first week of Mehr, end of Mehr, autumn, winter
DATES = ["2026-09-30", "2026-10-21", "2026-11-25", "2027-01-20"]

SCRIPT = """
import json, seed, db, students, manager
from datetime import date
seed.run()
t = manager.today()
with db.conn() as c:
    flagged = {sid: [s["type"] for s in students.facts(c, sid, t)["signals"]] for sid in range(1, 31)}
    alerts = [a["type"] for a in manager.collect(c)["alerts"]]
print(json.dumps({"flagged": {k: v for k, v in flagged.items() if v}, "alerts": alerts}))
"""

@pytest.mark.parametrize("day", DATES)
def test_planted_stories_show_up(day):
    tmp = tempfile.mkdtemp(prefix="javid-story-")
    env = {**os.environ, "DB_PATH": os.path.join(tmp, "school.db"), "SCHOOL_PATH": os.path.join(tmp, "school.json"),
           "DEMO_TODAY": day, "LLM_API_KEY": "x", "EMBED_API_KEY": "x"}   # no model is called, but the clients need a key
    out = subprocess.run([sys.executable, "-c", SCRIPT], cwd=ROOT, env=env, capture_output=True, text=True, check=True)
    r = json.loads(out.stdout.strip().splitlines()[-1])
    flagged = {int(k): v for k, v in r["flagged"].items()}
    # counselor: the math decline (student 1) and the absences (student 2), and nobody else by chance
    assert "grade" in flagged.get(1, []), f"{day}: declining student not flagged {flagged}"
    assert "absence" in flagged.get(2, []), f"{day}: absent student not flagged {flagged}"
    assert set(flagged) == {1, 2}, f"{day}: unexpected students flagged {flagged}"
    # manager: the late teacher and the absent student
    assert "teacher_late" in r["alerts"] and "student_absent" in r["alerts"], f"{day}: {r['alerts']}"
