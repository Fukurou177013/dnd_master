# D&D Master: архитектура проекта

**Статус:** канонический документ для coding-агента.
**Обновлено:** 2026-11-17, сверено с кодом в `backend/app`, `frontend/src`, `backend/tests`.
**Правило:** если этот файл расходится с кодом или тестами — правда в коде; обнови этот файл в той же задаче.

## 1. Что это

Веб-приложение, в котором пользователь регистрируется, создаёт персонажа, создаёт личную
кампанию и обменивается сообщениями с «мастером». Мастер — текстовая LLM: она описывает
сцену и последствия, но **не управляет механикой**. Броски, модификаторы и сложность
считает сервер на Python; правила для ответа ищутся в SRD 5.2.1 через pgvector.

## 2. Стек и порты

| Часть | Технологии | Адрес |
|---|---|---|
| Frontend | React 19, TypeScript, Vite, react-router | `http://localhost:5173` |
| Backend | Python 3.14+, FastAPI, SQLAlchemy 2 async, Alembic | `http://localhost:8000` (`/docs`, `/health`) |
| БД | PostgreSQL 17 + pgvector, Docker Compose | `localhost:5433` снаружи |
| LLM | Любой OpenAI-совместимый API: `/chat/completions`, `/embeddings` | базовый URL из `LLM_BASE_URL` |

Локальная бесплатная конфигурация — Ollama (`http://localhost:11434/v1`). Фактические
значения лежат в `backend/.env`; агент не открывает этот файл. Шаблон — `backend/.env.example`.

## 3. Структура

```text
backend/
  app/
    api/deps.py            cookie-сессия -> текущий пользователь
    api/v1/                auth, characters, campaigns, rules, router
    core/config.py         настройки, проверки при старте
    core/security.py       Argon2, хеширование токена сессии
    core/loop.py           selector event loop для Windows
    db/                    Base, async-подключение
    models/                users, sessions, characters, campaigns,
                           campaign_memories, campaign_messages, srd_chunks
    rules/character_options.py  виды, классы, навыки, расчёты, валидация
    schemas/               Pydantic-контракты API
    services/
      auth.py sessions.py characters.py campaigns.py
      dice.py              d20 и проверки
      game_master.py       prompt, ход, резюме, идемпотентность
      retrieval.py         поиск SRD через pgvector
      llm.py               HTTP-клиент и провайдеры
      rate_limit.py        лимит сообщений в памяти процесса
    scripts/import_srd.py  разбиение корпуса и импорт embeddings
  alembic/                 миграции схемы
  data/srd/                локальный корпус SRD (не в Git, ~1.6 МБ)
  tests/                   pytest + fake-провайдеры
frontend/src/              api.ts, AuthContext, страницы, types.ts
start.bat                  запуск БД + backend + frontend; `start.bat stop`
docs/ARCHITECTURE.md       этот файл
AGENTS.md                  правила для агента и команды
OPENCODE_GO_POLICY.md      политика провайдера
```

## 4. Поток одного хода

Эндпоинт: `POST /api/v1/campaigns/{campaign_id}/messages`.

1. Cookie-сессия проверяется в `api/deps.py`; запросы к кампании фильтруются по владельцу.
2. Проверяется лимит `chat_rate_limit_per_minute` (по умолчанию 30/мин на пользователя).
3. Загружается кампания, её персонаж и последние сообщения.
4. Если в запросе есть `check`, сервер сам бросает d20 (`secrets`), считает модификатор,
   бонус мастерства и сравнивает с DC. Клиент не может передать результат броска.
5. Пользовательское сообщение сохраняется. `client_message_id` делает повтор идемпотентным:
   при повторном запросе возвращается уже сохранённый обмен.
6. Выполняется поиск SRD: embedding вопроса, косинусное расстояние в pgvector, top-k=4.
7. Собирается prompt: системная инструкция + резюме кампании + результат проверки +
   найденные фрагменты SRD + последние 12 сообщений.
8. Вызывается LLM; ответ сохраняется вместе с броском и источниками.
9. В `BackgroundTasks` планируется обновление структурированного резюме отдельным вызовом.

Дополнительно действует advisory-lock на кампанию (`pg_advisory_xact_lock`), чтобы
параллельные запросы не создавали дубликаты. Нумерация сообщений — `sequence`, уникальна
внутри кампании.

Ошибки:
- retrieval упал → ответ без источников, ход продолжается;
- таймаут LLM → `504`, сообщение пользователя уже сохранено, безопасный повтор;
- провайдер недоступен → `503`, сообщение сохранено;
- неверная проверка/навык/DC → `422`;
- частые сообщения → `429`;
- нет владения кампанией/персонажем → `404`.

## 5. API (`/api/v1`)

| Метод и путь | Назначение |
|---|---|
| `POST /auth/register` | регистрация, `201` |
| `POST /auth/login` | вход, ставит httpOnly cookie |
| `GET /auth/me` | текущий пользователь |
| `POST /auth/logout` | выход, `204` |
| `GET/POST /characters` | список и создание персонажа |
| `GET/PATCH/DELETE /characters/{id}` | чтение, изменение, удаление |
| `GET /rules/character-options` | доступные виды, классы, предыстории, навыки |
| `GET/POST /campaigns` | список и создание личной кампании |
| `GET/DELETE /campaigns/{id}` | чтение и удаление |
| `GET /campaigns/{id}/messages?limit=` | история, `limit` 1..500 (по умолчанию 100) |
| `POST /campaigns/{id}/messages` | ход мастера |

Все ответы с персонажами/кампаниями проверяют владельца. `password_hash` и токены
сессий наружу не отдаются.

## 6. Данные

- `users` — email в нижнем регистре, Argon2-хеш пароля.
- `sessions` — хранится только хеш токена, срок жизни и метаданные.
- `characters` — характеристики 1..30, уровень 1..20, вычисляемые HP/AC/speed проверяются
  сервером; произвольные данные — в `data` (JSONB).
- `campaigns` — владелец + принадлежащий ему персонаж.
- `campaign_memories` — структурированное резюме: `facts`, `goals`, `npcs`, `locations`,
  `open_threads`.
- `campaign_messages` — роль, текст, `sequence`, `client_message_id`, `metadata` (бросок,
  источники). Уникальность: `(campaign_id, sequence)` и `(campaign_id, client_message_id)`.
- `srd_chunks` — `source`, `section`, `title`, `content`, `license`, `embedding VECTOR(1024)`,
  HNSW-индекс с `vector_cosine_ops`, уникальный `chunk_key`.

## 7. Инварианты, которые нельзя ломать

1. Механика — только сервер: кубик, модификаторы, DC, успех/провал. Модель не придумывает
   броски и не меняет результат.
2. Модель не выдумывает правила: факты берутся из найденных фрагментов SRD и резюме;
   если фрагментов нет — честно сообщает об этом.
3. Все выборы персонажа валидируются по серверному каталогу; клиенту не доверяем.
4. Любой доступ к персонажу/кампании фильтруется по `user_id`.
5. Повтор запроса с тем же `client_message_id` не создаёт второй обмен.
6. Ошибка обновления резюме не отменяет ход и не теряет журнал сообщений.
7. Секреты и `.env` не попадают в клиент, логи, ответы и Git.
8. Провайдер модели заменяем через `ChatProvider`/`EmbeddingProvider`; тесты используют
   fake-провайдеры и фиксированный кубик.

## 8. Конфигурация (значения по умолчанию)

| Переменная | По умолчанию | Смысл |
|---|---|---|
| `RETRIEVAL_TOP_K` | 4 | сколько фрагментов SRD попадает в prompt |
| `RECENT_MESSAGE_LIMIT` | 12 | сколько последних сообщений видит модель |
| `MAX_MESSAGE_LENGTH` | 4000 | максимум символов в сообщении |
| `CHAT_RATE_LIMIT_PER_MINUTE` | 30 | лимит ходов на пользователя |
| `LLM_TIMEOUT_SECONDS` | 30 | таймаут HTTP-запроса к модели |
| `LLM_MAX_OUTPUT_TOKENS` | 700 | максимум токенов ответа |
| `LLM_TEMPERATURE` | 0.7 | температура ответа |
| `LLM_EMBEDDING_DIMENSIONS` | 1024 | обязана совпадать со схемой `srd_chunks` |

При старте `config.py` отклоняет: `SameSite=None` без `Secure`, wildcard в CORS,
размерность embeddings, отличную от 1024.

## 9. Тесты

`backend/tests` — pytest с PostgreSQL-базой `dnd_test` (по умолчанию
`postgresql+psycopg://dnd:dnd@localhost:5433/dnd_test`). Фикстуры создают схему,
включают pgvector, очищают таблицы, подменяют LLM, embeddings и кубик.
Покрыты: auth, characters, campaigns/ход, идемпотентность, память, rate limit,
security, config. Реальный ключ модели для тестов не нужен.

## 10. Известные расхождения и ограничения (на 2026-11-17)

- `OPENCODE_GO_POLICY.md` заявляет, что `config.py` отклоняет Go-эндпоинт при старте.
  В текущем коде такой проверки **нет** (есть только SameSite, CORS, embeddings).
  Политика обязательна для агента, но технически пока не обеспечена.
- В коде `LLM_BASE_URL` по умолчанию — OpenAI, а не Ollama. Рабочая локальная
  конфигурация задаётся в `backend/.env`; при пустом `LLM_API_KEY` провайдер вернёт `503`.
- У кампании нет вступительной сцены: чат начинается с пустого состояния.
- Свободный текст не распознаётся как отдельное намерение «осмотреться»: проверку
  пользователь задаёт явно.
- Политика контента не реализована.
- CI и формального стандарта сообщений коммитов нет.
- `backend/data/srd/srd-5.2.1.md` — данные, а не документация: не читать целиком.

## 11. Куда смотреть при изменениях

| Что меняется | Файлы |
|---|---|
| Настройки и проверки старта | `backend/app/core/config.py`, `backend/tests/test_config.py` |
| Системная инструкция, prompt, ход, резюме | `backend/app/services/game_master.py` |
| Поиск SRD и формат источников | `backend/app/services/retrieval.py` |
| LLM/embeddings и ошибки | `backend/app/services/llm.py` |
| Кампании, сообщения, память | `backend/app/services/campaigns.py`, `backend/app/api/v1/campaigns.py` |
| Схема таблиц | `backend/app/models/` |
| Броски и правила персонажа | `backend/app/services/dice.py`, `backend/app/rules/character_options.py` |
| Импорт SRD | `backend/app/scripts/import_srd.py` |
| Cookie-сессии и доступ | `backend/app/core/security.py`, `backend/app/api/deps.py` |
| Frontend-запросы и типы | `frontend/src/api.ts`, `frontend/src/types.ts` |

История решений и roadmap — в `docs/human/ARCHITECTURE_GUIDE_2026.md` (для человека,
не для агента). Команды запуска и проверок — в `AGENTS.md`.
