import pytest

from app.rules.intent import SEARCH_DC, detect_search_intent


@pytest.mark.parametrize(
    "text",
    [
        "Я осматриваюсь.",
        "Я оглядываюсь.",
        "Я смотрю вокруг.",
        "Что я вижу вокруг?",
        "Что вокруг меня находится?",
        "Хочу понять, что вокруг меня находится.",
        "Я осматриваю окрестности.",
        "Я изучаю обстановку.",
        "Я осматриваю комнату.",
    ],
)
def test_passive_observation_needs_no_check(text: str) -> None:
    intent = detect_search_intent(text)
    assert intent.kind == "passive"
    assert intent.ability is None
    assert intent.skill is None
    assert intent.dc == SEARCH_DC


@pytest.mark.parametrize(
    ("text", "ability", "skill"),
    [
        ("Я ищу следы на полу.", "intelligence", "Investigation"),
        ("Я ищу тайник в стене.", "intelligence", "Investigation"),
        ("Я осматриваю труп.", "intelligence", "Investigation"),
        ("Я обшариваю сундук.", "intelligence", "Investigation"),
        ("Я проверяю следы у двери.", "intelligence", "Investigation"),
        ("Я прислушиваюсь к двери.", "wisdom", "Perception"),
        ("Я вглядываюсь в темноту.", "wisdom", "Perception"),
        ("Я высматриваю часовых.", "wisdom", "Perception"),
    ],
)
def test_active_search_uses_server_check(
    text: str,
    ability: str,
    skill: str,
) -> None:
    intent = detect_search_intent(text)
    assert intent.kind == "check"
    assert intent.ability == ability
    assert intent.skill == skill
    assert intent.dc == SEARCH_DC


@pytest.mark.parametrize(
    "text",
    [
        "Я ищу.",
        "Я осматриваю.",
        "Я поищу.",
    ],
)
def test_ambiguous_search_asks_for_clarification(text: str) -> None:
    intent = detect_search_intent(text)
    assert intent.kind == "ambiguous"
    assert intent.ability is None
    assert intent.skill is None


@pytest.mark.parametrize("text", ["Я ищу выход.", "Я ищу ключ.", "Я ищу свидетелей."])
def test_search_with_object_is_not_ambiguous(text: str) -> None:
    intent = detect_search_intent(text)
    assert intent.kind == "passive"
