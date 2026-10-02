# ISK — Blitz Cloud MVP

Единый Telegram-бот + Mini App для тестового запуска ISK на blitz.cloud.

## Что изменено для Blitz

- Один контейнер вместо двух отдельных backend/frontend контейнеров.
- React собирается внутри root `Dockerfile`.
- FastAPI раздаёт готовый Mini App.
- PostgreSQL подключается через переменную `DATABASE_URL`, которую может предоставить managed database Blitz.
- Redis для текущего MVP не требуется.
- Приложение слушает `$PORT` и по умолчанию использует `8080`.
- HTTPS предоставляет blitz.cloud.

Blitz умеет собирать GitHub-проект с root Dockerfile и подключать managed PostgreSQL. См. документацию Blitz.

## Переменные окружения

Обязательные:

- `BOT_TOKEN` — токен Telegram-бота.
- `DATABASE_URL` — строка подключения PostgreSQL.
- `WEBAPP_URL` — HTTPS-адрес Mini App.

Опциональные:

- `ADMIN_IDS`
- `CORS_ORIGINS`
- `LOG_LEVEL`
- `REDIS_URL`

## Развёртывание на Blitz

1. Создать GitHub repository и загрузить содержимое этого проекта.
2. В blitz.cloud выбрать **Host something new → My own code**.
3. Выбрать GitHub repository.
4. На шаге базы данных включить PostgreSQL, если Blitz предложит его автоматически или через **Give it a database**.
5. Убедиться, что Dockerfile выбран из корня проекта.
6. Задать `BOT_TOKEN`.
7. После получения HTTPS-адреса приложения установить `WEBAPP_URL` равным этому адресу.
8. Перезапустить приложение.

## Важно

Это тестовый MVP. Перед production нужны webhook вместо polling, миграции Alembic, RBAC, резервное копирование/контроль восстановления, более строгая валидация платежей, мониторинг и полноценные интеграции провайдеров.

Модуль Sherlock сейчас использует демонстрационный provider и не является полноценным внешним сервисом.
