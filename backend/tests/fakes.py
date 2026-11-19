from app.core.config import settings
from app.services.llm import ChatMessage

SUMMARY_SYSTEM_MARKER = "Верни только JSON"
INTRO_SYSTEM_MARKER = "Начни кампанию"

DEFAULT_SUMMARY_JSON = (
    '{"facts": ["Герой вошёл в подземелье"], '
    '"goals": ["Найти реликвию"], '
    '"npcs": ["Страж ворот"], '
    '"locations": ["Подземелье"], '
    '"open_threads": ["Дверь заперта"]}'
)

DEFAULT_INTRO = (
    "Вы просыпаетесь в тесной каморке над таверной. За окном моросит дождь, "
    "а внизу шумит вечерняя толпа. На столе лежит записка с незнакомой "
    "печатью: «Приходи к северным воротам до полуночи». За дверью слышны "
    "тяжёлые шаги. Что вы сделаете?"
)


class FakeChatProvider:
    def __init__(self) -> None:
        self.calls: list[list[ChatMessage]] = []
        self.fail_next: Exception | None = None
        self.fail_next_summary: Exception | None = None
        self.answer = "Мастер описывает исход. Источник: [1]."
        self.intro_response = DEFAULT_INTRO
        self.summary_response: str = DEFAULT_SUMMARY_JSON

    def _select(self, kind: str) -> list[list[ChatMessage]]:
        if kind == "summary":
            marker = SUMMARY_SYSTEM_MARKER
        elif kind == "intro":
            marker = INTRO_SYSTEM_MARKER
        else:
            markers = (SUMMARY_SYSTEM_MARKER, INTRO_SYSTEM_MARKER)
            return [
                call
                for call in self.calls
                if not any(marker in call[0].content for marker in markers)
            ]
        return [call for call in self.calls if marker in call[0].content]

    @property
    def summary_calls(self) -> list[list[ChatMessage]]:
        return self._select("summary")

    @property
    def intro_calls(self) -> list[list[ChatMessage]]:
        return self._select("intro")

    @property
    def answer_calls(self) -> list[list[ChatMessage]]:
        return self._select("answer")

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float,
        max_tokens: int,
    ) -> str:
        del temperature, max_tokens
        self.calls.append(list(messages))
        system = messages[0].content
        is_summary = SUMMARY_SYSTEM_MARKER in system
        is_intro = INTRO_SYSTEM_MARKER in system
        if is_summary and self.fail_next_summary is not None:
            error = self.fail_next_summary
            self.fail_next_summary = None
            raise error
        if not is_summary and self.fail_next is not None:
            error = self.fail_next
            self.fail_next = None
            raise error
        if is_summary:
            return self.summary_response
        if is_intro:
            return self.intro_response
        return self.answer


class FakeEmbeddingProvider:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        vector = [0.0] * settings.llm_embedding_dimensions
        vector[0] = 1.0
        return [list(vector) for _ in texts]


class FixedRollGenerator:
    def __init__(self, d20: int = 20) -> None:
        self.d20 = d20
        self.calls = 0

    def roll_d20(self) -> int:
        self.calls += 1
        return self.d20
