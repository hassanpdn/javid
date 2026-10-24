"""Rule: SQLite allows one writer. Parallel users must not cause 'database is locked' or double work."""
import concurrent.futures as cf
from conftest import Client, db, add_letter, run_agent

def test_parallel_agents_never_handle_a_letter_twice():
    for i in range(6):
        add_letter(f"همزمان آزمون {i}", "بخشنامه برای اطلاع همه مدارس است.")
    with cf.ThreadPoolExecutor(4) as ex:
        list(ex.map(lambda _: run_agent(), range(4)))
    with db() as c:
        rows = c.execute("""SELECT l.id, COUNT(*) n FROM agent_log g JOIN letters l ON l.id = g.letter_id
                            WHERE l.subject LIKE 'همزمان آزمون%' AND g.action LIKE 'نامه را خواند%' GROUP BY l.id""").fetchall()
        waiting = c.execute("SELECT COUNT(*) FROM letters WHERE subject LIKE 'همزمان آزمون%' AND status IN ('new', 'processing')").fetchone()[0]
    assert waiting == 0 and len(rows) == 6 and all(r["n"] == 1 for r in rows)

def test_parallel_writes():
    def work(i):
        return [Client("vali").post("/parent/forms/wellbeing", {"data": {"mood": 1, "school_worry": 5}}).status_code,
                Client("moshaver").post("/counselor/students/3/notes", {"note": f"یادداشت {i}"}).status_code,
                Client("edari").post("/notifications/read-all").status_code]
    with cf.ThreadPoolExecutor(12) as ex:
        codes = sum(ex.map(work, range(36)), [])
    assert set(codes) == {200}
