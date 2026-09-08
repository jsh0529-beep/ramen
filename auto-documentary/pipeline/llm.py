"""LLM 어댑터 — Google Gemini(LangChain) 우선, 없으면 None 반환(템플릿 모드)."""
from __future__ import annotations

import json
import logging
import re
from typing import Optional, Protocol

from .config import Settings

log = logging.getLogger(__name__)


class LLM(Protocol):
    def complete(self, system: str, prompt: str) -> str: ...


class GeminiLLM:
    """LangChain의 ChatGoogleGenerativeAI 래퍼. 미설치 시 google-generativeai SDK로 대체."""

    def __init__(self, api_key: str, model: str):
        self.model = model
        self._chat = None
        self._genai_model = None
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            self._chat = ChatGoogleGenerativeAI(model=model, google_api_key=api_key, temperature=0.4)
        except ImportError:
            import google.generativeai as genai  # type: ignore
            genai.configure(api_key=api_key)
            self._genai_model = genai.GenerativeModel(model)

    def complete(self, system: str, prompt: str) -> str:
        if self._chat is not None:
            from langchain_core.messages import HumanMessage, SystemMessage
            res = self._chat.invoke([SystemMessage(content=system), HumanMessage(content=prompt)])
            return res.content if isinstance(res.content, str) else str(res.content)
        res = self._genai_model.generate_content(f"{system}\n\n{prompt}")
        return res.text


def get_llm(settings: Settings) -> Optional[LLM]:
    if not settings.can_use_gemini:
        log.info("LLM 비활성화 (offline=%s, key=%s) → 템플릿 모드", settings.offline, bool(settings.gemini_api_key))
        return None
    return GeminiLLM(settings.gemini_api_key, settings.gemini_model)


def parse_json_block(text: str) -> Optional[dict]:
    """LLM 응답에서 JSON 객체를 안전하게 추출."""
    if not text:
        return None
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    candidate = m.group(1) if m else text[text.find("{"): text.rfind("}") + 1]
    try:
        return json.loads(candidate)
    except (json.JSONDecodeError, ValueError):
        log.warning("LLM 응답 JSON 파싱 실패")
        return None
