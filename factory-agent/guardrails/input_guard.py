from __future__ import annotations

import re

from config.logging_config import get_logger

logger = get_logger("input_guard")


class InputValidationError(Exception):
    pass


class UnsupportedQuestionError(InputValidationError):
    pass


class InputGuard:
    BLOCKED_PATTERNS: list[str] = [
        r"ignore\s+(all\s+)?(prior|instructions|previous)",
        r"forget\s+(all\s+)?(prior|instructions|previous)",
        r"system\s+prompt",
        r"you\s+are\s+(now|an?)\s+",
        r"print\s+your\s+(prompt|instructions)",
        r"reveal\s+(your\s+)?(prompt|instructions)",
        r"bypass\s+(the\s+)?(safeguards|guardrails|restrictions)",
    ]

    @staticmethod
    def sanitize_query(query: str) -> str:
        return query.strip()[:2000]

    @staticmethod
    def detect_blocked_patterns(query: str) -> None:
        for pattern in InputGuard.BLOCKED_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                raise InputValidationError(
                    f"Query contains blocked pattern: {pattern}"
                )

    @staticmethod
    def validate_query(query: str) -> str:
        if not query or not query.strip():
            raise InputValidationError("Empty query")
        query = InputGuard.sanitize_query(query)
        InputGuard.detect_blocked_patterns(query)
        return query
