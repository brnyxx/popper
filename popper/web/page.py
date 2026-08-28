"""AC8 - 단일 페이지 렌더러.

첫 응답 한 번으로 화면이 완성되도록 서버가 페어와 카운터와 룰을 미리 박아
넣는다. 브라우저가 추가 왕복을 해야 첫 페어가 보이는 구조가 아니다.

템플릿은 popper/web/index.html 한 장뿐이고 외부 자산을 전혀 참조하지 않는다.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from html import escape
from pathlib import Path
from typing import Sequence

from popper.web.state import RuleView, Snapshot

logger = logging.getLogger(__name__)

TEMPLATE_PATH = Path(__file__).resolve().parent / "index.html"

TOKEN_BOOT = "{{BOOT_JSON}}"
TOKEN_AXIS_LABEL = "{{AXIS_LABEL}}"
TOKEN_LEFT_TEXT = "{{LEFT_TEXT}}"
TOKEN_RIGHT_TEXT = "{{RIGHT_TEXT}}"
TOKEN_REMAINING = "{{REMAINING}}"
TOKEN_ELIMINATED = "{{ELIMINATED}}"
TOKEN_RULES = "{{RULES}}"


class TemplateMissing(RuntimeError):
    """단일 페이지 템플릿을 찾지 못했다."""


@lru_cache(maxsize=None)
def _template() -> str:
    try:
        return TEMPLATE_PATH.read_text(encoding="utf-8")
    except OSError as e:
        logger.exception("단일 페이지 템플릿을 읽지 못했다: %s", TEMPLATE_PATH)
        raise TemplateMissing(f"템플릿을 읽지 못했다: {TEMPLATE_PATH}") from e


def _script_safe_json(payload: object) -> str:
    """script 블록 안에서 조기 종료를 일으키지 않도록 꺾쇠와 앰퍼샌드를 이스케이프한다."""
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return raw.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def render_rules(rules: Sequence[RuleView]) -> str:
    """컴파일 페인 목록의 서버 사이드 마크업."""
    return "".join(
        '<li><span class="rule-axis">{axis}</span>'
        '<span class="rule-text">{text}</span></li>'.format(
            axis=escape(rule.axis_label), text=escape(rule.text)
        )
        for rule in rules
    )


def render_page(snapshot: Snapshot) -> str:
    """스냅샷 하나를 완성된 단일 페이지 HTML로 만든다."""
    pair = snapshot.pair
    replacements = (
        (TOKEN_BOOT, _script_safe_json(snapshot.to_dict())),
        (TOKEN_AXIS_LABEL, escape(pair.axis_label)),
        (TOKEN_LEFT_TEXT, escape(pair.left_text)),
        (TOKEN_RIGHT_TEXT, escape(pair.right_text)),
        (TOKEN_REMAINING, f"{snapshot.remaining_combinations:,}"),
        (TOKEN_ELIMINATED, str(snapshot.eliminated_pairs)),
        (TOKEN_RULES, render_rules(snapshot.rules)),
    )
    page = _template()
    for token, value in replacements:
        page = page.replace(token, value)
    return page
