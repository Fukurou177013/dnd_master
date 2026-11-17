> Для человека: пошаговая инструкция локального запуска и настройки.
> Правила для coding-агента и команды проверок — `../AGENTS.md`,
> краткая архитектура — `../docs/ARCHITECTURE.md`.

# D&D Master: вертикальный срез

Минимальный браузерный сценарий: регистрация → персонаж → личная кампания → чат с мастером по SRD 5.2.1. Мастер отвечает по-русски, сервер сам считает проверки и броски d20, а история и структурированное резюме сохраняются между запросами.

## Что уже работает

- Регистрация и вход по email/паролю, пароль хранится как Argon2id-хеш, сессия — в httpOnly cookie.
- Ограниченный каталог стартовых опций SRD: виды, классы, предыстории и навыки.
- Сервер выводит хиты, класс брони, скорость, бонус владения, инициативу, спасброски и модификаторы навыков. Клиентские значения этих полей не считаются авторитетными.
- Личные кампании, журнал сообщений и отдельное структурированное резюме.
- Поиск по SRD-фрагментам через PostgreSQL + pgvector (RAG) и ответы со ссылками на разделы.
- Проверки характеристик и навыков: сервер бросает d20, применяет модификатор и сохраняет d20 / модификатор / DC / итог / успех.
- Повтор запроса с тем же `client_message_id` не дублирует сообщения и не перебрасывает кубик.
- Тесты не требуют реального LLM-ключа: провайдер подменяется fake-адаптером.

## Термины

- **SRD** — System Reference Document, открытая часть правил D&D 5e (SRD 5.2.1) под лицензией Creative Commons.
- **RAG** — Retrieval-Augmented Generation: перед ответом модель получает найденные по смыслу фрагменты правил.
- **Embedding** — числовой вектор смысла текста. Поиск сравнивает вектор запроса с векторами фрагментов.
- **pgvector** — расширение PostgreSQL для хранения векторов и поиска по косинусному расстоянию.
- **Alembic** — инструмент миграций схемы базы данных для SQLAlchemy.
- **DC** — Difficulty Class, сложность проверки. Итог d20 + модификатор должен быть не меньше DC.
- **Cookie-сессия** — браузер автоматически отправляет httpOnly cookie; JavaScript не может прочитать токен.
- **Vite proxy** — dev-сервер фронтенда пересылает `/api` в FastAPI, поэтому браузер видит один origin и cookie работает.

## Требования

- Python 3.14+ и [uv](https://docs.astral.sh/uv/).
- Docker Desktop (или другой Docker Engine) для PostgreSQL 17 с pgvector.
- Node.js 22+ и npm для фронтенда.
- Ключ и URL LLM/embeddings-провайдера, совместимого с OpenAI API. Без ключа интерфейс работает, но чат вернёт управляемую ошибку 503.

## Шаг 1. Запустить PostgreSQL

Из каталога `backend`:

```powershell
docker compose up -d db
docker compose ps
```

База слушает `localhost:5433` (не 5432), пользователь/пароль/база — `dnd/dnd/dnd`. Образ `pgvector/pgvector:pg17` уже содержит расширение `vector`; миграция включает его командой `CREATE EXTENSION IF NOT EXISTS vector`.

## Шаг 2. Настроить окружение backend

```powershell
cd backend
Copy-Item .env.example .env
uv sync
```

Откройте `backend/.env` и заполните:

```dotenv
DATABASE_URL=postgresql+psycopg://dnd:dnd@localhost:5433/dnd
COOKIE_SECURE=false
SESSION_TTL_DAYS=30
SESSION_COOKIE_SAMESITE=lax
CORS_ORIGINS=

LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=ollama
LLM_CHAT_MODEL=qwen3:14b
LLM_EMBEDDING_MODEL=qwen3-embedding-cpu
LLM_EMBEDDING_DIMENSIONS=1024
LLM_TIMEOUT_SECONDS=120
LLM_SYSTEM_SUFFIX=/no_think
```

`.env` уже в `.gitignore`. Не коммитьте ключи. Клиент фронтенда ключ не видит: все вызовы провайдера идут с backend.

Важно: размерность embeddings в настройках должна совпадать с колонкой `srd_chunks.embedding` (`vector(1024)`) — иначе приложение не запустится, проверка выполняется при старте. Если меняете модель на другую размерность, обновите `EMBEDDING_DIMENSIONS` в `app/core/config.py`, создайте миграцию и заново импортируйте корпус.

### Локальный режим без облачного LLM (Ollama)

Проект по умолчанию рассчитан на локальные модели:

```powershell
ollama pull qwen3:14b
ollama pull qwen3-embedding:0.6b

# Эмбеддинги на CPU: на 12 ГБ VRAM они не помещаются рядом с qwen3:14b
@"
FROM qwen3-embedding:0.6b
PARAMETER num_gpu 0
"@ | Set-Content Modelfile.embedding
ollama create qwen3-embedding-cpu -f Modelfile.embedding
```

- `qwen3:14b` отвечает в чате. `LLM_SYSTEM_SUFFIX=/no_think` отключает режим рассуждений Qwen3: ответ приходит примерно за 20 секунд вместо 70 и не упирается в `LLM_MAX_OUTPUT_TOKENS`. Для облачных моделей оставляйте суффикс пустым.
- `qwen3-embedding:0.6b` — многоязычная embedding-модель на 1024 измерения: русский запрос находит английские разделы SRD. Вариант с `PARAMETER num_gpu 0` даёт те же векторы, но не занимает VRAM, поэтому модели не выгружают друг друга и ход остаётся быстрым.

Чтобы перейти на облачного провайдера, укажите его `LLM_BASE_URL`, `LLM_API_KEY` и модель, затем поменяйте `EMBEDDING_DIMENSIONS` в `app/core/config.py` (например, 1536 для `text-embedding-3-small`), создайте миграцию под новую размерность и импортируйте корпус заново.

Особенности локального режима:

- На Windows backend запускается с `--loop app.core.loop:selector_loop_factory`: psycopg не работает с ProactorEventLoop, который uvicorn использует по умолчанию.
- Если включён квантованный KV-кэш (`OLLAMA_KV_CACHE_TYPE=q8_0`), Ollama нужно запускать с `OLLAMA_FLASH_ATTENTION=1`. Для RTX 3060 12 ГБ модель qwen3:14b целиком помещается в VRAM при `OLLAMA_CONTEXT_LENGTH=12288`.

## Шаг 3. Применить миграции

```powershell
uv run alembic upgrade head
uv run alembic current
```

Ожидаемая голова: `5d9b1e4a7c20`. Команда создаёт таблицы `campaigns`, `campaign_memories`, `campaign_messages`, `srd_chunks` и расширение `vector`.

## Шаг 4. Импортировать SRD-корпус

Корпус в репозиторий не входит. SRD 5.2.1 распространяется по CC BY 4.0: скачайте официальный PDF с `https://www.dndbeyond.com/srd` или готовую Markdown-конвертацию и сохраните файл локально, например `backend/data/srd/srd-5.2.1.md`.

Поддерживаются:

- Markdown/текст с заголовками `#`, `##`, `###`: разделы режутся по заголовкам, длинные — по абзацам.
- JSONL, по одному объекту на строку: `{"section": "...", "title": "...", "content": "..."}`.

Импорт:

```powershell
uv run python -m app.scripts.import_srd data/srd/srd-5.2.1.md `
  --source "SRD 5.2.1" `
  --source-url "https://www.dndbeyond.com/srd" `
  --license "CC BY 4.0"
```

Импорт идемпотентен: ключ фрагмента — SHA-256 от источника, раздела и текста. Повторный запуск пропускает уже сохранённые фрагменты. Атрибуция (`source`, `section`, `license`, `source_url`) хранится в БД и возвращается в ответах чата.

## Шаг 5. Запустить backend

```powershell
uv run uvicorn app.main:app --reload --port 8000 --loop app.core.loop:selector_loop_factory
```

Проверка:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Ожидается `{"status": "ok"}`. Интерактивная документация: `http://localhost:8000/docs`.

## Шаг 6. Запустить frontend

В отдельном терминале:

```powershell
cd frontend
npm install
npm run dev
```

Откройте `http://localhost:5173`. Vite пересылает `/api` на `http://localhost:8000`, поэтому cookie сессии отправляется как same-origin. В `frontend/vite.config.ts` оставлено `changeOrigin: false`: backend проверяет `Origin`, и подмена `Host` на `localhost:8000` привела бы к отказу state-changing запросов.

## Шаг 7. Пройти сценарий

1. Зарегистрируйтесь (пароль от 12 символов) и войдите.
2. На вкладке «Персонажи» создайте персонажа: вид, класс, предыстория, характеристики, навыки.
3. Проверьте, что HP, КБ, скорость и модификаторы рассчитал сервер.
4. На вкладке «Кампании» создайте кампанию и выберите персонажа.
5. В чате отправьте действие. При необходимости включите «Проверка», выберите характеристику, навык и DC.
6. В ответе появятся текст мастера, карточка броска и раскрывающийся список источников SRD.
7. Обновите страницу: история и блок «Память кампании» должны сохраниться.

## API

Все маршруты начинаются с `/api/v1`.

| Метод | Путь | Назначение |
| --- | --- | --- |
| POST | `/auth/register` | Регистрация |
| POST | `/auth/login` | Вход и установка cookie |
| GET | `/auth/me` | Текущий пользователь |
| POST | `/auth/logout` | Выход |
| GET | `/rules/character-options` | Каталог видов, классов, предысторий, навыков |
| GET/POST | `/characters` | Список и создание персонажей |
| GET/PATCH/DELETE | `/characters/{id}` | Чтение, изменение, удаление |
| GET/POST | `/campaigns` | Список и создание кампаний |
| GET/DELETE | `/campaigns/{id}` | Кампания с резюме |
| GET | `/campaigns/{id}/messages` | История сообщений |
| POST | `/campaigns/{id}/messages` | Отправить действие и получить ответ |

Пример запроса с проверкой:

```json
{
  "content": "Я осматриваю комнату.",
  "client_message_id": "0f5c1d9e-6a15-4c5c-8c8e-2d4e4f4a9e11",
  "check": {
    "ability": "wisdom",
    "skill": "Perception",
    "dc": 15
  }
}
```

`client_message_id` генерируется клиентом один раз на попытку. При ошибке 503/504 повторите тот же запрос с тем же идентификатором: пользовательское сообщение уже сохранено, дубликата не будет, бросок не изменится.

Чужие персонажи и кампании возвращают 404, а не 403, чтобы не раскрывать их существование.

## Тесты

Тесты используют отдельную базу `dnd_test` на том же контейнере (`localhost:5433`). При старте она создаётся автоматически, схема пересоздаётся через SQLAlchemy metadata, таблицы очищаются между тестами.

```powershell
cd backend
uv run pytest -q
```

Внимание: не направляйте тесты на рабочую базу. По умолчанию используется `dnd_test`; при необходимости переопределите `TEST_DB_NAME`, `TEST_DATABASE_URL` и `TEST_ADMIN_URL`.

Тесты не требуют реального LLM-ключа. В `tests/conftest.py` подменяются:

- `get_chat_provider` — fake-ответы мастера и резюме;
- `get_embedding_provider` — детерминированные векторы;
- `get_roll_generator` — фиксированный d20.

Проверяются изоляция аккаунтов, правила персонажа, детерминированный бросок, источники, идемпотентность и повтор после ошибки провайдера.

## Линтеры и сборка

```powershell
cd backend
uv run ruff check app tests
uv run alembic upgrade head

cd ../frontend
npm run lint
npm run build
```

## Переменные окружения

| Переменная | Назначение |
| --- | --- |
| `DATABASE_URL` | Async URL SQLAlchemy, например `postgresql+psycopg://...` |
| `COOKIE_SECURE` | `true` только для HTTPS |
| `SESSION_TTL_DAYS` | Срок жизни cookie-сессии |
| `SESSION_COOKIE_SAMESITE` | `lax`, `strict` или `none`. Комбинация `none` без `COOKIE_SECURE=true` отклоняется при старте: браузеры не сохраняют SameSite=None cookie без Secure |
| `CORS_ORIGINS` | Список origin через запятую, если фронтенд не через proxy. Wildcard `*` запрещён и отклоняется при старте, потому что API использует cookie-сессии |
| `LLM_BASE_URL` | База OpenAI-совместимого API |
| `LLM_API_KEY` | Секретный ключ, только backend |
| `LLM_CHAT_MODEL` | Модель чата |
| `LLM_EMBEDDING_MODEL` | Модель embeddings |
| `LLM_EMBEDDING_DIMENSIONS` | Размерность вектора. Должна равняться `EMBEDDING_DIMENSIONS` (1024) из `app/core/config.py`, иначе приложение не запустится |
| `LLM_TIMEOUT_SECONDS` | Тайм-аут запросов к провайдеру |
| `LLM_MAX_OUTPUT_TOKENS` | Ограничение длины ответа |
| `RETRIEVAL_TOP_K` | Сколько фрагментов SRD передавать в prompt |
| `RECENT_MESSAGE_LIMIT` | Сколько последних сообщений входит в prompt |
| `CHAT_RATE_LIMIT_PER_MINUTE` | Лимит сообщений на пользователя в минуту |

## Безопасность и ограничения

- Пароли и токены сессий не попадают в ответы API; в БД хранится SHA-256 токена.
- Для state-changing запросов с заголовком `Origin` проверяется same-origin или список `CORS_ORIGINS`.
- Есть лимит длины сообщения (4000 символов) и простой in-memory rate limit. Для нескольких процессов нужен общий rate limiter (Redis и т.п.).
- Резюме обновляется отдельным вызовом модели. Если обновление не удалось, сообщения остаются, а старое резюме не затирается.
- В этом срезе характеристики принимаются в диапазоне 3–18; строгая проверка standard array/point buy, брони и полного боевого листа — следующий этап.
- Вне среза: email-подтверждение, восстановление пароля, совместные кампании, бой, полный каталог заклинаний, поиск по истории, production deployment.
