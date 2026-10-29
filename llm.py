import os, re, json
from contextvars import ContextVar
from openai import OpenAI
from dotenv import load_dotenv
import access

load_dotenv()
client = OpenAI(base_url=os.getenv("LLM_BASE_URL"), api_key=os.getenv("LLM_API_KEY"))
MODEL = os.getenv("LLM_MODEL")
# Extra request fields one provider needs and another rejects, as JSON, e.g. {"enable_thinking": false}
EXTRA = json.loads(os.getenv("LLM_EXTRA") or "{}")
# "/no_think" is how a local Qwen3 (Ollama) is told not to think first; a hosted API uses LLM_EXTRA instead
NO_THINK = "" if os.getenv("LLM_NO_THINK") == "0" else "\n/no_think"

# Which assistant the current request belongs to («school», «fabric»). app.py sets it for every API call, because the
# AI switch is per assistant (access.ai_on).
assistant = ContextVar("assistant", default="school")

class ModelOff(Exception):
    """The AI of this assistant is switched off: the caller answers with text built by code (offline.py)."""

def ai_on():
    return access.ai_on(assistant.get())

def ask_llm(system, user, max_tokens=500, temperature=0.2):
    if not ai_on():
        raise ModelOff()
    r = client.chat.completions.create(
        model=MODEL, temperature=temperature, max_tokens=max_tokens,
        messages=[{"role": "system", "content": system + NO_THINK},
                  {"role": "user", "content": user}],
        extra_body=EXTRA or None,
    )
    text = r.choices[0].message.content or ""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()

def ask_json(system, user, max_tokens=300):
    """Ask for a JSON object. Returns a dict, or None if the model didn't give valid JSON."""
    text = ask_llm(system + "\nفقط یک شیء JSON معتبر برگردان، بدون هیچ توضیح اضافه.", user,
                   max_tokens=max_tokens, temperature=0)
    match = re.search(r"\{.*\}", text, flags=re.S)
    try:
        return json.loads(match.group(0)) if match else None
    except ValueError:
        return None
