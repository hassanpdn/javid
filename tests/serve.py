"""Start the app for tests: fake model, a fresh demo database in a temp folder, and uvicorn.
Used by tests/conftest.py, and by the browser tests (frontend/playwright.config.js runs `python tests/serve.py`)."""
import os, subprocess, sys, tempfile, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fake_llm

APP_PORT, LLM_PORT = int(os.getenv("TEST_APP_PORT", "8765")), int(os.getenv("TEST_LLM_PORT", "11500"))
TODAY = "2026-10-25"   # 3 Aban 1405, so tests always see the same school days

def start():
    """Returns (uvicorn process, base url). The fake model runs in this process (fake_llm.MODE controls it)."""
    fake_llm.start(LLM_PORT)
    tmp = tempfile.mkdtemp(prefix="javid-test-")
    llm = f"http://127.0.0.1:{LLM_PORT}/v1"
    env = {**os.environ, "DB_PATH": os.path.join(tmp, "school.db"), "CHROMA_PATH": os.path.join(tmp, "db"),
           "LLM_BASE_URL": llm, "EMBED_BASE_URL": llm, "LLM_API_KEY": "x", "EMBED_API_KEY": "x",
           "LLM_MODEL": "fake", "EMBED_MODEL": "fake", "DEMO_TODAY": TODAY, "KEEP_DB": "1",
           "SIMILARITY_THRESHOLD": "0.1"}
    for script in ("seed.py", "ingest.py"):
        subprocess.run([sys.executable, script], cwd=ROOT, env=env, check=True, capture_output=True)
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app:app", "--port", str(APP_PORT)],
                            cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{APP_PORT}"
    for _ in range(100):
        try:
            urllib.request.urlopen(base + "/", timeout=1)
            return proc, base, env["DB_PATH"]
        except Exception:
            time.sleep(0.2)
    proc.kill()
    raise RuntimeError("app did not start")

if __name__ == "__main__":
    proc, base, _ = start()
    print("ready on", base, flush=True)
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
