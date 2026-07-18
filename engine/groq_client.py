import os
import json
import socket
import urllib.request
import urllib.error
from typing import List, Optional

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "llama-3.3-70b-versatile"
TIMEOUT_SECONDS = 5.0


def get_explanation(
    reason_codes: List[str],
    changed_name: str,
    affected_name: str
) -> Optional[str]:
    """
    Calls the Groq API to generate a brief, plain-English explanation for why changing
    `changed_name` might affect `affected_name`, based ONLY on the provided `reason_codes`.

    Reads the API key from the GROQ_API_KEY environment variable.
    Returns None on any failure (missing key, timeout, network error, invalid response)
    to ensure the core deterministic analysis is never interrupted.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Groq API explanation skipped: GROQ_API_KEY environment variable is not set.")
        return None

    if not reason_codes:
        reason_str = "potential indirect coupling"
    else:
        reason_str = ", ".join(reason_codes)

    prompt = (
        f"Changed item: {changed_name}\n"
        f"Affected item: {affected_name}\n"
        f"Reason codes: {reason_str}"
    )

    payload = {
        "model": DEFAULT_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a concise software dependency assistant. Explain in 1-2 plain English sentences "
                    "why changing the specified code item may affect the affected item. Base your answer strictly "
                    "on the provided reason codes and names. Do not invent file paths, logic details, or functions "
                    "not mentioned in the prompt."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.2,
        "max_tokens": 100
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "RippleGuard/1.0"
    }

    try:
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(GROQ_API_URL, data=req_data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
            if response.status == 200:
                body = json.loads(response.read().decode("utf-8"))
                explanation = body["choices"][0]["message"]["content"].strip()
                return explanation
            else:
                print(f"Groq API returned HTTP status {response.status}")
                return None
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, socket.timeout, json.JSONDecodeError, KeyError, IndexError, OSError) as e:
        print(f"Groq API call failed: {type(e).__name__}: {e}")
        return None
