from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from config.logging_config import get_logger

logger = get_logger("intent_detector")


@dataclass
class Intent:
    skill_name: str
    confidence: float
    entities: dict[str, Any] = field(default_factory=dict)


class IntentDetector:
    HELP_PATTERNS: list[str] = [
        r"^(hi|hello|hey|help|thanks|thank you)\b",
        r"what\s+data\s+do\s+you\s+have",
        r"what\s+.*\b(access|acess)\b.*\b(to|too)\b",
        r"what\s+.*\b(can|could)\b.*\b(access|acess)\b",
        r"what\s+can\s+you\s+do",
        r"what\s+.*\bcapabilit(y|ies)\b",
        r"show\s+me\s+the\s+data",
        r"list\s+the\s+datasets",
        r"what\s+datasets?\s+(do\s+you\s+have|are\s+available)",
    ]

    SKILL_PATTERNS: dict[str, list[str]] = {
        "material_sufficiency": [
            r"(enough|sufficient|sufficiency|available|availability).*(material|stock|inventory)",
            r"(material|stock|inventory).*(enough|sufficient|sufficiency|available|availability)",
            r"can\s+we\s+(fulfill|fulfill|produce|make)",
            r"do\s+we\s+have\s+(enough|sufficient)",
            r"check\s+(material|stock|inventory)\s+(for|of)",
        ],
        "machine_requirements": [
            r"(machine|machinery|equipment).*(require|need|time|hour)",
            r"(require|need).*(machine|machinery|equipment)",
            r"machine\s+(time|hour|requirement)",
            r"what\s+(machine|machinery|equipment)",
            r"how\s+much\s+(machine|time)",
        ],
        "material_risk_report": [
            r"(risk|risky|shortage|short).*(material|report)",
            r"(material|supply).*(risk|risky|shortage|report)",
            r"risk\s+report",
            r"what\s+(material|item|supply).*(at\s+risk|short|need|reorder)",
            r"reorder",
            r"generate.*report",
        ],
    }

    ORDER_ID_PATTERN = re.compile(r"(ORD[-_]?\d+)", re.IGNORECASE)

    def detect(self, query: str) -> Intent:
        query_lower = query.lower()

        for pattern in self.HELP_PATTERNS:
            if re.search(pattern, query_lower):
                logger.info(
                    "Intent detected",
                    extra={
                        "skill": "help",
                        "confidence": 1.0,
                        "entities": {},
                    },
                )
                return Intent(skill_name="help", confidence=1.0, entities={})

        best_skill = "unknown"
        best_score = 0.0
        best_entities: dict[str, Any] = {}

        order_match = self.ORDER_ID_PATTERN.search(query)
        if order_match:
            best_entities["order_id"] = order_match.group(1).upper()

        for skill_name, patterns in self.SKILL_PATTERNS.items():
            score = 0.0
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    score += 1.0 / len(patterns)
            if score > best_score:
                best_score = score
                best_skill = skill_name

        logger.info(
            "Intent detected",
            extra={
                "skill": best_skill,
                "confidence": best_score,
                "entities": best_entities,
            },
        )

        return Intent(
            skill_name=best_skill,
            confidence=best_score,
            entities=best_entities,
        )
