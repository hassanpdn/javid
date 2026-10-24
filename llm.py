import os, re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(base_url=os.getenv("LLM_BASE_URL"), api_key=os.getenv("LLM_API_KEY"))
MODEL = os.getenv("LLM_MODEL")

def ask_llm(system, user, max_tokens=500, temperature=0.2):
    r = client.chat.completions.create(
        model=MODEL, temperature=temperature, max_tokens=max_tokens,
        messages=[{"role": "system", "content": system + "\n/no_think"},
                  {"role": "user", "content": user}],
    )
    text = r.choices[0].message.content or ""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()

def ask_json(system, user, max_tokens=300):
    """Ask for a JSON object. Returns a dict, or None if the model didn't give valid JSON."""
    import json
    text = ask_llm(system + "\nفقط یک شیء JSON معتبر برگردان، بدون هیچ توضیح اضافه.", user,
                   max_tokens=max_tokens, temperature=0)
    match = re.search(r"\{.*\}", text, flags=re.S)
    try:
        return json.loads(match.group(0)) if match else None
    except ValueError:
        return None
