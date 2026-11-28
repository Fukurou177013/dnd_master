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

SPECIES_DARKVISION = {
    "Dragonborn": 60,
    "Dwarf": 120,
    "Elf": 60,
    "Gnome": 60,
    "Goliath": 0,
    "Halfling": 0,
    "Human": 0,
    "Orc": 120,
    "Tiefling": 60,
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

BACKGROUND_ABILITY_SCORES = {
    "Acolyte": ("intelligence", "wisdom", "charisma"),
    "Criminal": ("dexterity", "constitution", "intelligence"),
    "Sage": ("constitution", "intelligence", "wisdom"),
    "Soldier": ("strength", "dexterity", "constitution"),
    "Wayfarer": ("dexterity", "wisdom", "charisma"),
}

BACKGROUND_BONUS_MODES = (
    {"key": "two_one", "label": "+2 / +1", "values": (2, 1)},
    {"key": "one_one_one", "label": "+1 / +1 / +1", "values": (1, 1, 1)},
)
BACKGROUND_BONUS_MAX_SCORE = 20

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

ABILITY_SCORE_METHODS = ("manual", "standard_array", "point_buy", "roll_4d6")
STANDARD_ARRAY = (15, 14, 13, 12, 10, 8)
ROLL_STAT_DICE_COUNT = 4
ROLL_STAT_DICE_SIDES = 6
ROLL_STAT_DICE_DROP_LOWEST = 1
POINT_BUY_BUDGET = 27
POINT_BUY_MIN = 8
POINT_BUY_MAX = 15
POINT_BUY_COSTS = {
    8: 0,
    9: 1,
    10: 2,
    11: 3,
    12: 4,
    13: 5,
    14: 7,
    15: 9,
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


def ability_generation_options() -> dict[str, Any]:
    return {
        "score_range": {"min": 3, "max": 18},
        "methods": [
            {
                "key": "point_buy",
                "label": "Покупка очков",
                "budget": POINT_BUY_BUDGET,
                "min": POINT_BUY_MIN,
                "max": POINT_BUY_MAX,
                "costs": {str(score): cost for score, cost in POINT_BUY_COSTS.items()},
            },
            {
                "key": "standard_array",
                "label": "Стандартный массив",
                "values": list(STANDARD_ARRAY),
            },
            {
                "key": "roll_4d6",
                "label": "Бросок 4d6 (без худшего)",
                "dice": {
                    "count": ROLL_STAT_DICE_COUNT,
                    "sides": ROLL_STAT_DICE_SIDES,
                    "drop_lowest": ROLL_STAT_DICE_DROP_LOWEST,
                },
            },
            {"key": "manual", "label": "Вручную"},
        ],
    }


def character_options() -> dict[str, Any]:
    return {
        "abilities": [
            {"key": key, "label": ABILITY_LABELS[key]} for key in ABILITIES
        ],
        "species": [
            {
                "name": name,
                "speed": speed,
                "darkvision": SPECIES_DARKVISION[name],
            }
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
            {
                "name": name,
                "skills": list(skills),
                "ability_scores": list(BACKGROUND_ABILITY_SCORES[name]),
            }
            for name, skills in sorted(BACKGROUND_SKILLS.items())
        ],
        "skills": [
            {"name": name, "ability": ability}
            for name, ability in sorted(SKILL_ABILITIES.items())
        ],
        "level": {"min": 1, "max": 20},
        "background_ability_bonus": {
            "max_score": BACKGROUND_BONUS_MAX_SCORE,
            "modes": [
                {
                    "key": mode["key"],
                    "label": mode["label"],
                    "values": list(mode["values"]),
                }
                for mode in BACKGROUND_BONUS_MODES
            ],
        },
        "ability_generation": ability_generation_options(),
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


def _canonical_ability_score_method(value: str) -> str:
    return _canonical_option(value, ABILITY_SCORE_METHODS)


def _read_stored_background_bonus(data: Any) -> dict[str, int]:
    if not isinstance(data, dict):
        return {}
    raw = data.get("background_ability_bonus")
    if not isinstance(raw, dict):
        return {}
    bonus: dict[str, int] = {}
    for ability in ABILITIES:
        value = raw.get(ability)
        if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 2:
            bonus[ability] = value
    return bonus


def _validate_background_ability_bonus(
    background: str,
    raw: Any,
) -> dict[str, int]:
    if not isinstance(raw, dict):
        raise CharacterRulesError(
            "Бонусы характеристик от предыстории должны быть объектом"
        )
    allowed = set(BACKGROUND_ABILITY_SCORES[background])
    bonus: dict[str, int] = {}
    for key, value in raw.items():
        if key not in ABILITIES:
            raise CharacterRulesError(
                f"Неизвестная характеристика в бонусе предыстории: {key}"
            )
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or not 0 <= value <= 2
        ):
            raise CharacterRulesError(
                "Бонус характеристики от предыстории должен быть от 0 до 2"
            )
        if value > 0 and key not in allowed:
            raise CharacterRulesError(
                f"Предыстория {background} не даёт бонус к характеристике "
                f"{ABILITY_LABELS[key]}"
            )
        bonus[key] = value

    positive = sorted(score for score in bonus.values() if score > 0)
    if positive not in ([1, 1, 1], [1, 2]):
        raise CharacterRulesError(
            f"Бонусы предыстории {background}: выберите +2/+1 или +1/+1/+1"
        )
    return {ability: bonus.get(ability, 0) for ability in ABILITIES}


def _validate_ability_scores(
    method: str,
    scores: dict[str, int],
) -> None:
    if method in ("manual", "roll_4d6"):
        return

    if method == "standard_array":
        if sorted(scores.values()) != sorted(STANDARD_ARRAY):
            raise CharacterRulesError(
                "Стандартный массив требует ровно значения 15, 14, 13, 12, 10, 8"
            )
        return

    if method == "point_buy":
        total = 0
        for ability, score in scores.items():
            if not POINT_BUY_MIN <= score <= POINT_BUY_MAX:
                raise CharacterRulesError(
                    f"При покупке очков {ABILITY_LABELS[ability]} "
                    f"должна быть от {POINT_BUY_MIN} до {POINT_BUY_MAX}"
                )
            total += POINT_BUY_COSTS[score]
        if total > POINT_BUY_BUDGET:
            raise CharacterRulesError(
                f"Перерасход очков характеристик: {total} из {POINT_BUY_BUDGET}"
            )


def _resolve_ability_score_method(
    values: dict[str, Any],
    *,
    existing: Any | None,
    existing_method: str | None,
    scores: dict[str, int],
) -> str | None:
    method = values.get("ability_score_method", existing_method)
    if method is None:
        if existing is None:
            raise CharacterRulesError("Укажите метод генерации характеристик")
        if any(ability in values for ability in ABILITIES):
            raise CharacterRulesError("Укажите метод генерации характеристик")
        return None

    method = _canonical_ability_score_method(str(method))
    _validate_ability_scores(method, scores)
    return method


def build_character_values(
    values: dict[str, Any],
    *,
    existing: Any | None = None,
) -> dict[str, Any]:
    existing_method: str | None = None
    existing_bonus: dict[str, int] = {}
    base: dict[str, Any] = {}
    if existing is not None:
        existing_data = getattr(existing, "data", None)
        if isinstance(existing_data, dict):
            existing_method = existing_data.get("ability_score_method")
            existing_bonus = _read_stored_background_bonus(existing_data)
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

    if "background_ability_bonus" in values:
        background_bonus = _validate_background_ability_bonus(
            background, values["background_ability_bonus"]
        )
    elif existing is None:
        raise CharacterRulesError(
            "Укажите бонусы характеристик от предыстории"
        )
    elif not any(existing_bonus.values()):
        background_bonus = {ability: 0 for ability in ABILITIES}
    else:
        if existing.background != background:
            raise CharacterRulesError(
                "Укажите бонусы характеристик для новой предыстории"
            )
        background_bonus = _validate_background_ability_bonus(
            background, existing_bonus
        )

    scores: dict[str, int] = {}
    base_scores: dict[str, int] = {}
    for ability in ABILITIES:
        if ability in values:
            final_score = values[ability]
        elif existing is not None:
            final_score = getattr(existing, ability)
        else:
            final_score = base[ability]
        if (
            not isinstance(final_score, int)
            or not 3 <= final_score <= BACKGROUND_BONUS_MAX_SCORE
        ):
            raise CharacterRulesError(
                f"Характеристика {ABILITY_LABELS[ability]} с бонусом предыстории "
                f"должна быть от 3 до {BACKGROUND_BONUS_MAX_SCORE}"
            )
        base_score = final_score - background_bonus[ability]
        if not 3 <= base_score <= 18:
            raise CharacterRulesError(
                f"Характеристика {ABILITY_LABELS[ability]} до бонуса предыстории "
                "должна быть от 3 до 18"
            )
        scores[ability] = final_score
        base_scores[ability] = base_score

    data = dict(base.get("data") or {})
    ability_score_method = _resolve_ability_score_method(
        values,
        existing=existing,
        existing_method=existing_method,
        scores=base_scores,
    )
    data.pop("ability_score_method", None)
    if ability_score_method is not None:
        data["ability_score_method"] = ability_score_method
    data["background_ability_bonus"] = background_bonus

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
            "darkvision": SPECIES_DARKVISION[species],
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
