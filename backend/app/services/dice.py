from __future__ import annotations

import secrets
from typing import Any

from app.models import Character
from app.rules.character_options import (
    ABILITY_LABELS,
    SKILL_ABILITIES,
    CharacterRulesError,
    ability_modifier,
    proficiency_bonus,
)


class RollGenerator:
    def roll_d20(self) -> int:
        return secrets.randbelow(20) + 1


_default_generator = RollGenerator()


def get_roll_generator() -> RollGenerator:
    return _default_generator


def _canonical_ability(value: str) -> str:
    normalized = value.strip().casefold()
    for ability in ABILITY_LABELS:
        if ability == normalized:
            return ability
    raise CharacterRulesError(f"Недопустимая характеристика: {value}")


def _canonical_skill(value: str) -> str:
    normalized = value.strip().casefold()
    for skill in SKILL_ABILITIES:
        if skill.casefold() == normalized:
            return skill
    raise CharacterRulesError(f"Недопустимый навык: {value}")


def resolve_check(
    character: Character,
    *,
    ability: str,
    skill: str | None,
    dc: int,
    generator: RollGenerator,
) -> dict[str, Any]:
    ability_key = _canonical_ability(ability)

    skill_name: str | None = None
    if skill is not None:
        skill_name = _canonical_skill(skill)
        skill_ability = SKILL_ABILITIES[skill_name]
        if skill_ability != ability_key:
            raise CharacterRulesError(
                f"Навык {skill_name} относится к характеристике "
                f"{ABILITY_LABELS[skill_ability]}"
            )

    score = getattr(character, ability_key)
    modifier = ability_modifier(score)
    proficient = False
    if skill_name is not None:
        proficiencies = character.data.get("skill_proficiencies", [])
        proficient = skill_name in proficiencies
        if proficient:
            modifier += proficiency_bonus(character.level)
    if not 5 <= dc <= 30:
        raise CharacterRulesError("Сложность проверки должна быть от 5 до 30")

    d20 = generator.roll_d20()
    if not 1 <= d20 <= 20:
        raise CharacterRulesError("Генератор броска вернул недопустимое значение")

    total = d20 + modifier
    return {
        "kind": "skill" if skill_name else "ability",
        "ability": ability_key,
        "ability_label": ABILITY_LABELS[ability_key],
        "skill": skill_name,
        "d20": d20,
        "modifier": modifier,
        "proficient": proficient,
        "dc": dc,
        "total": total,
        "success": total >= dc,
    }
