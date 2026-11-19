from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from app.rules.character_options import SKILL_ABILITIES

SEARCH_DC = 15

IntentKind = Literal["passive", "check", "ambiguous"]


@dataclass(frozen=True)
class SearchIntent:
    kind: IntentKind
    ability: str | None = None
    skill: str | None = None
    dc: int = SEARCH_DC


_INVESTIGATION = re.compile(
    r"(?:"
    r"\b(?:ищ|поищ|поиск)\w*\s+"
    r"(?:след|улик|тайник|потай|скрыт|ловушк|секрет|ход)\w*"
    r"|\b(?:обыскива|обшарива|прочесыва)\w*"
    r"|\bосматрива\w*\s+(?:труп|тело|останк|вещ|карман|сундук|ящик)\w*"
    r"|\b(?:изуча|проверя)\w*\s+(?:след|улик)\w*"
    r"|\bроюсь\b"
    r")"
)

_PERCEPTION = re.compile(
    r"(?:"
    r"\bприслушива\w*|\bвслушива\w*|\bпринюхива\w*"
    r"|\bвысматрива\w*|\bвглядыва\w*"
    r"|\bищ\w*\s+(?:взгляд|глазами|кого|что-то|что то)\w*"
    r")"
)

_PASSIVE = re.compile(
    r"(?:"
    r"\bосматриваюсь\b|\bоглядываюсь\b|\bосмотреться\b|\bоглядеться\b"
    r"|\bсмотрю\s+вокруг\b"
    r"|\bоглядыва\w*\s+(?:окрестност|вокруг|обстановк)\w*"
    r"|\bосматрива\w*\s+(?:окрестност|обстановк)\w*"
    r"|\bчто\s+(?:я\s+)?вижу(?:\s+вокруг)?\b|\bчто\s+вокруг\b"
    r"|\bчто\s+(?:здесь|тут)\b"
    r"|\bизуча\w*\s+обстановк\w*|\bоценива\w*\s+обстановк\w*"
    r"|\bхочу\s+понять,\s+что\s+вокруг\b"
    r")"
)

_AMBIGUOUS = re.compile(
    r"(?:"
    r"\b(?:ищу|ищ|поищу)\s*[.!?…]*$"
    r"|\bосматриваю\s*(?:$|[.,!?])"
    r")"
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold().replace("ё", "е")).strip()


def _skill_check(skill: str) -> SearchIntent:
    return SearchIntent(
        kind="check",
        ability=SKILL_ABILITIES[skill],
        skill=skill,
    )


def detect_search_intent(text: str) -> SearchIntent:
    normalized = _normalize(text)
    if _INVESTIGATION.search(normalized):
        return _skill_check("Investigation")
    if _PERCEPTION.search(normalized):
        return _skill_check("Perception")
    if _PASSIVE.search(normalized):
        return SearchIntent(kind="passive")
    if _AMBIGUOUS.search(normalized):
        return SearchIntent(kind="ambiguous")
    return SearchIntent(kind="passive")
