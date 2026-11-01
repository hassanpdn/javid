import os, re, json
from contextvars import ContextVar
from openai import OpenAI, APIError
from dotenv import load_dotenv
import access

load_dotenv()
# Seconds to wait for one model answer. The browser gives up on a read after 20 s (lib/api.js), so the model must
# answer well before that; past this, the screen gets the text built by code. A slow local model can raise it.
TIMEOUT = float(os.getenv("LLM_TIMEOUT") or 15)
# No silent retries: two more tries would triple the wait the user sits through.
client = OpenAI(base_url=os.getenv("LLM_BASE_URL"), api_key=os.getenv("LLM_API_KEY"), timeout=TIMEOUT, max_retries=0)
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

class ModelDown(ModelOff):
    """The model did not answer in time, could not be reached or answered with an error. A kind of ModelOff, so
    every caller falls back to the same text built by code; nothing built from it is kept, and the next request
    tries the model again."""

def ai_on():
    return access.ai_on(assistant.get())

def ask_llm(system, user, max_tokens=500, temperature=0.2, timeout=None):
    """timeout: seconds to wait for the answer (None: TIMEOUT). Raises ModelOff with the AI switched off and
    ModelDown when the model does not answer in time or fails."""
    if not ai_on():
        raise ModelOff()
    try:
        r = (client.with_options(timeout=timeout) if timeout else client).chat.completions.create(
            model=MODEL, temperature=temperature, max_tokens=max_tokens,
            messages=[{"role": "system", "content": system + NO_THINK},
                      {"role": "user", "content": user}],
            extra_body=EXTRA or None,
        )
    except APIError as e:   # timeout, no connection, or an error status from the provider
        raise ModelDown() from e
    text = r.choices[0].message.content or ""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()

def ask_json(system, user, max_tokens=300, timeout=None):
    """Ask for a JSON object. Returns a dict, or None if the model didn't give valid JSON."""
    text = ask_llm(system + "\nفقط یک شیء JSON معتبر برگردان، بدون هیچ توضیح اضافه.", user,
                   max_tokens=max_tokens, temperature=0, timeout=timeout)
    match = re.search(r"\{.*\}", text, flags=re.S)
    try:
        return json.loads(match.group(0)) if match else None
    except ValueError:
        return None
