"""
llm_utils.py — Shared LLM plumbing used by all modules.
Single home for JSON repair, parsing, and the base API call.
"""

import json
import re
from openai import OpenAI
import profile as p


def repair_json(raw: str) -> str:
    """
    Fix the most common LLM JSON mistake: ] used instead of } to close an object.
    Walks character-by-character, swaps ] -> } when innermost open bracket is {.
    """
    result, stack = [], []
    for ch in raw:
        if ch == "{":
            stack.append("{"); result.append(ch)
        elif ch == "[":
            stack.append("["); result.append(ch)
        elif ch == "}":
            if stack and stack[-1] == "{":
                stack.pop()
            result.append(ch)
        elif ch == "]":
            if stack and stack[-1] == "[":
                stack.pop(); result.append(ch)
            elif stack and stack[-1] == "{":
                stack.pop(); result.append("}")
            else:
                result.append(ch)
        else:
            result.append(ch)
    return "".join(result)


def parse_json(raw: str):
    """Strip markdown fences, repair brackets, then parse JSON."""
    raw = re.sub(r"^```(?:json)?", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"```$",          "", raw, flags=re.MULTILINE)
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return json.loads(repair_json(raw))


def call_llm(client: OpenAI, prompt: str,
             temperature: float = 0.2, max_tokens: int = 900) -> str:
    """Single wrapper for all Groq chat completions in this project."""
    response = client.chat.completions.create(
        model=p.MODEL,
        messages=[
            {"role": "system", "content": p.SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()
