# Avito Telegram Notifier

FastAPI-сервис для будущей доставки уведомлений Avito в Telegram-группы. Сейчас реализована Telegram-часть: запуск одного бота через long polling, команды `/start`, `/register`, `/chatid`, хранение зарегистрированных групп в SQLite через SQLAlchemy async и Alembic.

Avito OAuth, Avito Messenger API, webhooks и привязка аккаунтов Avito на этом этапе не реализованы.

## Переменные окружения

Создайте `.env` из примера:

```bash
cp .env.example .env
```

| Переменная | Обязательность | Значение по умолчанию | Описание |
| --- | --- | --- | --- |
| `APP_NAME` | Нет | `Avito Telegram Notifier` | Название приложения. |
| `APP_ENV` | Нет | `production` | `development`, `staging` или `production`. |
| `APP_HOST` | Нет | `0.0.0.0` | Хост Uvicorn. |
| `APP_PORT` | Нет | `8000` | Порт Uvicorn. |
| `LOG_LEVEL` | Нет | `INFO` | Уровень логирования. |
| `TELEGRAM_BOT_TOKEN` | Да | — | Токен Telegram-бота из BotFather. Храните только в `.env`. |
| `TELEGRAM_ADMIN_IDS` | Нет | пусто | Telegram user_id администраторов сервиса через запятую. |
| `DATABASE_URL` | Нет | `sqlite+aiosqlite:///./data/app.db` | URL базы данных. |

Никогда не коммитьте настоящий `TELEGRAM_BOT_TOKEN`, не вставляйте его в README, тесты или логи. Файл `.env` находится в `.gitignore`.

## Создание и настройка Telegram-бота

1. Откройте Telegram-бота `@BotFather`.
2. Выполните `/newbot`, задайте имя и username.
3. Скопируйте выданный токен в `TELEGRAM_BOT_TOKEN` в `.env`.
4. Узнайте свой Telegram user_id, например через специальных ботов для показа ID, и добавьте его в `TELEGRAM_ADMIN_IDS`:

   ```env
   TELEGRAM_ADMIN_IDS=123456789,987654321
   ```

5. Добавьте созданного бота в нужную группу.
6. Разрешите боту отправлять сообщения. Администратором группы бот быть не обязан, если он не ограничен и может писать сообщения.

## Команды бота

### `/start`

В личном чате показывает инструкцию по добавлению и регистрации группы. В группе кратко предлагает выполнить `/register`.

### `/register`

Выполняется только в `group` или `supergroup`. Команду может вызвать владелец группы, администратор группы или пользователь из `TELEGRAM_ADMIN_IDS`.

После успешной регистрации бот сохраняет:

- `chat_id`;
- название группы;
- тип чата;
- Telegram user_id регистратора;
- username регистратора, если он есть.

Повторный `/register` не создаёт дубль. Если запись была отключена, команда снова устанавливает `is_active=true`.

### `/chatid`

Выполняется только в группе владельцем, администратором или пользователем из `TELEGRAM_ADMIN_IDS`. Показывает название группы, `chat_id`, тип чата и статус регистрации в базе.

## Миграции

Применить миграции:

```bash
alembic upgrade head
```

Откатить все миграции:

```bash
alembic downgrade base
```

Первая миграция: `20260714_0001_create_telegram_chats.py`.

## Запуск локально

```bash
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Проверка health endpoint:

```bash
curl http://localhost:8000/health
```

## Запуск через Docker

```bash
docker compose up -d --build
```

Контейнер перед стартом приложения выполняет `alembic upgrade head`. SQLite-база хранится в volume `app-data` по пути `/app/data`, поэтому зарегистрированные группы не пропадают после пересоздания контейнера.

## Структура проекта

```text
app/database/              # async SQLAlchemy engine/session и Base
app/models/telegram_chat.py # модель зарегистрированной Telegram-группы
app/services/              # сервисный слой работы с БД
app/telegram/              # Application, handlers и permissions Telegram-бота
app/routers/health.py      # /health endpoint
alembic/                   # миграции базы данных
```

## Avito accounts authentication

This stage adds only Avito application authentication for multiple independent Avito accounts. Messenger APIs, message polling, webhooks, Telegram notification delivery, and account-to-group linking are intentionally not implemented yet.

The token client uses the official Avito OAuth client credentials token endpoint:

```text
POST https://api.avito.ru/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials&client_id=<client_id>&client_secret=<client_secret>
```

A successful token response contains `access_token`, `token_type`, and `expires_in`. Access tokens are not stored in the database: the app decrypts the account secret only immediately before requesting a token, caches the token in memory per account, and refreshes it before expiration.

### Required security variables

Generate a Fernet encryption key for encrypted `client_secret` storage:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Set it in `.env` as `APP_ENCRYPTION_KEY`. Also set a long random `ADMIN_API_KEY`; this key is accepted only through the `X-Admin-Key` header and must never be sent in query strings, Telegram chats, logs, or committed to GitHub.

```env
APP_ENCRYPTION_KEY=replace-with-generated-fernet-key
ADMIN_API_KEY=replace-with-long-random-admin-key
```

### Add an Avito account safely

Use only placeholder values in scripts/docs. Put real Avito credentials only into your deployed environment/admin call.

```bash
curl -X POST http://localhost:8000/api/v1/admin/avito-accounts \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: ${ADMIN_API_KEY}" \
  -d '{
    "name": "Авито 2 Ликвидация",
    "profile_id": 436756553,
    "client_id": "fake-client-id",
    "client_secret": "fake-client-secret"
  }'
```

The API response never includes `client_secret` or `access_token`.

### Verify credentials

```bash
curl -X POST http://localhost:8000/api/v1/admin/avito-accounts/1/verify \
  -H "X-Admin-Key: ${ADMIN_API_KEY}"
```

### List accounts

```bash
curl http://localhost:8000/api/v1/admin/avito-accounts \
  -H "X-Admin-Key: ${ADMIN_API_KEY}"
```

### Activate and deactivate

```bash
curl -X POST http://localhost:8000/api/v1/admin/avito-accounts/1/deactivate \
  -H "X-Admin-Key: ${ADMIN_API_KEY}"

curl -X POST http://localhost:8000/api/v1/admin/avito-accounts/1/activate \
  -H "X-Admin-Key: ${ADMIN_API_KEY}"
```

### Replacing a compromised secret

If a Client Secret is compromised, rotate it in Avito, then immediately update this service through the admin API. The new secret is encrypted before storage, `token_status` is reset, and the in-memory token cache is invalidated so a fresh token is requested on the next use.

Never send `client_secret` through Telegram and never store it in GitHub: Telegram chats and Git history are not appropriate secret stores, and leaked credentials can allow unauthorized Avito API access.
