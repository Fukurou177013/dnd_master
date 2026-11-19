from __future__ import annotations

import re
from dataclasses import dataclass

SAFE_REDIRECT = (
    "Я не буду развивать эту сцену: она нарушает правила безопасности. "
    "Давайте сместим фокус — опишите другое действие или тему, "
    "и история продолжится."
)

_MINOR = re.compile(
    r"(?:"
    r"несовершеннолетн\w*|малолетн\w*|младенц\w*|ребен\w*"
    r"|дет(?:и|ей|ям|ями|ях)\b"
    r"|дет(?:ств\w*|ский|ская|ское|ского|ской|скому|ским|ских)\b"
    r"|подрост\w*|школьник\w*|девочк\w*|мальчик\w*"
    r"|\bchild(?:ren|hood)?\b|\bkids?\b|\bminors?\b|\bunderage\b|\bteen(?:ager)?s?\b"
    r"|(?<!\w)(?:1[0-7]|[0-9])\s*-?\s*"
    r"(?:лет(?:н\w*)?|год(?:а|у|ом|е)?|years?[- ]old|y\.?o\.?)(?=\W|$)"
    r")",
    re.IGNORECASE,
)

_SEXUAL = re.compile(
    r"(?:"
    r"секс\w*|интим\w*|изнасил\w*|растл\w*|педофил\w*|груминг|соврат\w*|порн\w*|эрот\w*"
    r"|полов(?:ой|ые|ых|ая|ое)\s+(?:акт|связ|отнош)"
    r"|\bsex(?:ual\w*)?\b|\brape\b|\bgroom(?:ing)?\b|\bmolest(?:ed|ing)?\b"
    r")",
    re.IGNORECASE,
)

_VIOLENCE = re.compile(
    r"(?:"
    r"убива|убийств|убить|насили|пыт(?:к\w*|ать|ает|ают|ал(?:а|и|о)?|аю|аясь)\b"
    r"|муча|избива|калеч|расчлен|истяза|казн"
    r"|\btortur(?:e|es|ed|ing)\b|\bkill(?:s|ed|ing)?\b|\bviolence\b"
    r")",
    re.IGNORECASE,
)

_EXPLOIT = re.compile(
    r"(?:"
    r"торговл\w*\s+(?:людьми|детьми)"
    r"|принужд\w*\s+к\s+проституц"
    r"|сексуальн\w*\s+эксплуатац"
    r"|grooming|trafficking"
    r")",
    re.IGNORECASE,
)

_HATE = re.compile(
    r"(?:"
    r"призыв\w*\s+к\s+(?:ненавист|насили|травл|убийств|розн)"
    r"|разжига\w*\s+(?:ненавист|розн|вражд)"
    r"|травить\s+(?:реальн|людей|групп|народ)"
    r"|уничтож\w*\s+(?:реальн|всех)\s+\w+"
    r"|\b(?:hate|despise)\s+(?:all\s+)?(?:real|actual)\s+"
    r"(?:people|groups?|communities)\b"
    r"|\bcall(?:ing)?\s+for\s+(?:violence|hatred|harassment)\s+"
    r"(?:against|toward)\s+(?:real|actual)\s+"
    r"(?:people|groups?|communities)\b"
    r"|\bincit(?:e|es|ing)\s+(?:(?:real|actual)\s+)?"
    r"(?:violence|hatred|harassment)\s+against\s+"
    r"(?:real|actual)\s+(?:people|groups?|communities)\b"
    r")",
    re.IGNORECASE,
)

_HARM = re.compile(
    r"(?:"
    r"как\s+(?:сделать|собрать|изготовить|приготовить|смастерить)\s+"
    r"(?:бомб|взрывчат|яд(?:ови)|наркотик|оружи|самодельн)"
    r"|инструкц\w*\s+по\s+(?:изготовл|создан|сборк)\w*\s+"
    r"(?:бомб|взрывчат|яд|наркотик|оружи)"
    r"|как\s+(?:убить|отравить|похитить)\s+"
    r"(?:человек|ребен|женщин|мужчин|людей)"
    r"|практическ\w*\s+инструкц\w*\s+(?:причин|вред|убийств)"
    r"|\bhow\s+to\s+(?:make|build|assemble|manufacture)\s+"
    r"(?:a\s+)?(?:bomb|explosive|poison|weapon|drug)\b"
    r"|\binstructions?\s+(?:for|to)\s+"
    r"(?:making|building|assembling|manufacturing)\s+"
    r"(?:a\s+)?(?:bomb|explosive|poison|weapon|drug)\b"
    r"|\bhow\s+to\s+(?:kill|poison|kidnap)\s+"
    r"(?:a\s+)?(?:real\s+)?(?:person|people|woman|man)\b"
    r")",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str | None = None


def check_content(text: str) -> PolicyDecision:
    normalized = " ".join(text.casefold().replace("ё", "е").split())
    if not normalized.strip():
        return PolicyDecision(allowed=True)

    if _HARM.search(normalized):
        return PolicyDecision(False, "practical_harm")
    if _HATE.search(normalized):
        return PolicyDecision(False, "hate_incitement")
    if _EXPLOIT.search(normalized):
        return PolicyDecision(False, "exploitation")
    if _MINOR.search(normalized) and (
        _SEXUAL.search(normalized) or _VIOLENCE.search(normalized)
    ):
        return PolicyDecision(False, "minor_sexual_or_violence")
    return PolicyDecision(allowed=True)
