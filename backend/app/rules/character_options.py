from __future__ import annotations

from typing import Any

ABILITIES = (
    "strength",
    "dexterity",
    "constitution",
    "intelligence",
    "wisdom",
    "charisma",
)

ABILITY_LABELS = {
    "strength": "Сила",
    "dexterity": "Ловкость",
    "constitution": "Телосложение",
    "intelligence": "Интеллект",
    "wisdom": "Мудрость",
    "charisma": "Харизма",
}

SKILL_ABILITIES = {
    "Acrobatics": "dexterity",
    "Animal Handling": "wisdom",
    "Arcana": "intelligence",
    "Athletics": "strength",
    "Deception": "charisma",
    "History": "intelligence",
    "Insight": "wisdom",
    "Intimidation": "charisma",
    "Investigation": "intelligence",
    "Medicine": "wisdom",
    "Nature": "intelligence",
    "Perception": "wisdom",
    "Performance": "charisma",
    "Persuasion": "charisma",
    "Religion": "intelligence",
    "Sleight of Hand": "dexterity",
    "Stealth": "dexterity",
    "Survival": "wisdom",
}

SPECIES_SPEEDS = {
    "Aasimar": 30,
    "Dragonborn": 30,
    "Dwarf": 30,
    "Elf": 30,
    "Gnome": 30,
    "Goliath": 35,
    "Halfling": 30,
    "Human": 30,
    "Orc": 30,
    "Tiefling": 30,
}

CLASS_HIT_DICE = {
    "Barbarian": 12,
    "Bard": 8,
    "Cleric": 8,
    "Druid": 8,
    "Fighter": 10,
    "Monk": 8,
    "Paladin": 10,
    "Ranger": 10,
    "Rogue": 8,
    "Sorcerer": 6,
    "Warlock": 8,
    "Wizard": 6,
}

CLASS_SAVING_THROWS = {
    "Barbarian": ("strength", "constitution"),
    "Bard": ("dexterity", "charisma"),
    "Cleric": ("wisdom", "charisma"),
    "Druid": ("intelligence", "wisdom"),
    "Fighter": ("strength", "constitution"),
    "Monk": ("strength", "dexterity"),
    "Paladin": ("wisdom", "charisma"),
    "Ranger": ("strength", "dexterity"),
    "Rogue": ("dexterity", "intelligence"),
    "Sorcerer": ("constitution", "charisma"),
    "Warlock": ("wisdom", "charisma"),
    "Wizard": ("intelligence", "wisdom"),
}

BACKGROUND_SKILLS = {
    "Acolyte": ("Insight", "Religion"),
    "Criminal": ("Sleight of Hand", "Stealth"),
    "Sage": ("Arcana", "History"),
    "Soldier": ("Athletics", "Intimidation"),
    "Wayfarer": ("Insight", "Stealth"),
}

_ALL_SKILLS = tuple(SKILL_ABILITIES)

CLASS_SKILL_CHOICES = {
    "Barbarian": ("Animal Handling", "Athletics", "Intimidation", "Nature", "Perception", "Survival"),
    "Bard": _ALL_SKILLS,
    "Cleric": ("History", "Insight", "Medicine", "Persuasion", "Religion"),
    "Druid": (
        "Arcana",
        "Animal Handling",
        "Insight",
        "Medicine",
        "Nature",
        "Perception",
        "Religion",
        "Survival",
    ),
    "Fighter": (
        "Acrobatics",
        "Animal Handling",
        "Athletics",
        "History",
        "Insight",
        "Intimidation",
        "Perception",
        "Persuasion",
        "Survival",
    ),
    "Monk": ("Acrobatics", "Athletics", "History", "Insight", "Religion", "Stealth"),
    "Paladin": ("Athletics", "Insight", "Intimidation", "Medicine", "Persuasion", "Religion"),
    "Ranger": (
        "Animal Handling",
        "Athletics",
        "Insight",
        "Investigation",
        "Nature",
        "Perception",
        "Stealth",
        "Survival",
    ),
    "Rogue": (
        "Acrobatics",
        "Athletics",
        "Deception",
        "Insight",
        "Intimidation",
        "Investigation",
        "Perception",
        "Performance",
        "Persuasion",
        "Sleight of Hand",
        "Stealth",
    ),
    "Sorcerer": ("Arcana", "Deception", "Insight", "Intimidation", "Persuasion", "Religion"),
    "Warlock": (
        "Arcana",
        "Deception",
        "History",
        "Intimidation",
        "Investigation",
        "Nature",
        "Religion",
    ),
    "Wizard": ("Arcana", "History", "Insight", "Investigation", "Medicine", "Nature", "Religion"),
}

CLASS_SKILL_COUNTS = {
    "Bard": 3,
    "Ranger": 3,
    "Rogue": 4,
}


class CharacterRulesError(ValueError):
    pass


def ability_modifier(score: int) -> int:
    return (score - 10) // 2


def proficiency_bonus(level: int) -> int:
    return 2 + (level - 1) // 4


def _canonical_option(value: str, options: dict[str, Any] | tuple[str, ...]) -> str:
    normalized = value.strip().casefold()
    for option in options:
        if option.casefold() == normalized:
            return option
    raise CharacterRulesError(f"Недопустимое значение: {value}")


def _canonical_skill(value: str) -> str:
    return _canonical_option(value, SKILL_ABILITIES)


def character_options() -> dict[str, Any]:
    return {
        "abilities": [
            {"key": key, "label": ABILITY_LABELS[key]} for key in ABILITIES
        ],
        "species": [
            {"name": name, "speed": speed}
            for name, speed in sorted(SPECIES_SPEEDS.items())
        ],
        "classes": [
            {
                "name": name,
                "hit_die": hit_die,
                "saving_throws": list(CLASS_SAVING_THROWS[name]),
                "skill_choices": list(CLASS_SKILL_CHOICES[name]),
                "skill_count": CLASS_SKILL_COUNTS.get(name, 2),
            }
            for name, hit_die in sorted(CLASS_HIT_DICE.items())
        ],
        "backgrounds": [
            {"name": name, "skills": list(skills)}
            for name, skills in sorted(BACKGROUND_SKILLS.items())
        ],
        "skills": [
            {"name": name, "ability": ability}
            for name, ability in sorted(SKILL_ABILITIES.items())
        ],
        "level": {"min": 1, "max": 20},
    }


def _read_skill_proficiencies(data: dict[str, Any]) -> list[str]:
    raw = data.get("skill_proficiencies", data.get("skills", []))
    if raw is None:
        return []
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise CharacterRulesError("Навыки персонажа должны быть списком строк")
    return raw


def _validate_skills(
    species: str,
    character_class: str,
    background: str,
    data: dict[str, Any],
) -> list[str]:
    del species
    skills: list[str] = []
    seen: set[str] = set()
    for raw_skill in _read_skill_proficiencies(data):
        skill = _canonical_skill(raw_skill)
        if skill in seen:
            raise CharacterRulesError(f"Навык {skill} указан дважды")
        seen.add(skill)
        skills.append(skill)

    background_skills = set(BACKGROUND_SKILLS[background])
    class_choices = set(CLASS_SKILL_CHOICES[character_class])
    allowed = background_skills | class_choices
    for skill in skills:
        if skill not in allowed:
            raise CharacterRulesError(
                f"Навык {skill} недоступен для {character_class} / {background}"
            )

    class_skill_count = len((set(skills) - background_skills) & class_choices)
    max_class_skills = CLASS_SKILL_COUNTS.get(character_class, 2)
    if class_skill_count > max_class_skills:
        raise CharacterRulesError(
            f"{character_class} может выбрать не более {max_class_skills} классовых навыков"
        )
    return skills


def _derive_max_hp(level: int, hit_die: int, constitution_modifier: int) -> int:
    level_one = max(1, hit_die + constitution_modifier)
    per_level = max(1, hit_die // 2 + 1 + constitution_modifier)
    return level_one + per_level * (level - 1)


def build_character_values(
    values: dict[str, Any],
    *,
    existing: Any | None = None,
) -> dict[str, Any]:
    base: dict[str, Any] = {}
    if existing is not None:
        for field in (
            "name",
            "level",
            "species",
            "character_class",
            "background",
            *ABILITIES,
            "notes",
            "data",
        ):
            base[field] = getattr(existing, field)
    base.update(values)

    for field in ("name", "species", "character_class", "background", *ABILITIES):
        if base.get(field) is None:
            raise CharacterRulesError(f"Поле {field} обязательно")

    level = base["level"]
    if not isinstance(level, int) or not 1 <= level <= 20:
        raise CharacterRulesError("Уровень должен быть от 1 до 20")

    species = _canonical_option(str(base["species"]), SPECIES_SPEEDS)
    character_class = _canonical_option(str(base["character_class"]), CLASS_HIT_DICE)
    background = _canonical_option(str(base["background"]), BACKGROUND_SKILLS)

    scores = {ability: base[ability] for ability in ABILITIES}
    for ability, score in scores.items():
        if not isinstance(score, int) or not 3 <= score <= 18:
            raise CharacterRulesError(
                f"Характеристика {ABILITY_LABELS[ability]} должна быть от 3 до 18"
            )

    data = dict(base.get("data") or {})
    skill_proficiencies = _validate_skills(
        species, character_class, background, data
    )

    modifiers = {ability: ability_modifier(score) for ability, score in scores.items()}
    proficiency = proficiency_bonus(level)
    max_hp = _derive_max_hp(level, CLASS_HIT_DICE[character_class], modifiers["constitution"])
    armor_class = 10 + modifiers["dexterity"]
    speed = SPECIES_SPEEDS[species]

    skill_modifiers = {}
    for skill, ability in SKILL_ABILITIES.items():
        modifier = modifiers[ability]
        if skill in skill_proficiencies:
            modifier += proficiency
        skill_modifiers[skill] = modifier

    saving_throws = {}
    for ability in ABILITIES:
        modifier = modifiers[ability]
        if ability in CLASS_SAVING_THROWS[character_class]:
            modifier += proficiency
        saving_throws[ability] = modifier

    data.update(
        {
            "ability_modifiers": modifiers,
            "proficiency_bonus": proficiency,
            "initiative": modifiers["dexterity"],
            "passive_perception": 10 + skill_modifiers["Perception"],
            "skill_proficiencies": skill_proficiencies,
            "skill_modifiers": skill_modifiers,
            "saving_throws": saving_throws,
            "species_speed": speed,
        }
    )
    data.pop("skills", None)

    result = {
        "name": base["name"],
        "level": level,
        "species": species,
        "character_class": character_class,
        "background": background,
        **scores,
        "max_hp": max_hp,
        "armor_class": armor_class,
        "speed": speed,
        "notes": base.get("notes"),
        "data": data,
    }

    current_hp = values.get("current_hp")
    if current_hp is None:
        current_hp = (
            existing.current_hp
            if existing is not None and existing.current_hp <= max_hp
            else max_hp
        )
    if current_hp > max_hp:
        raise CharacterRulesError(
            f"Текущие хиты не могут превышать максимум ({max_hp})"
        )
    result["current_hp"] = current_hp
    return result
