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
