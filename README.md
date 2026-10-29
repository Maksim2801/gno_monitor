# GNO Monitor

Веб-приложение мониторинга и предиктивной аналитики состояния глубинно-насосного оборудования нефтяных скважин (дипломный проект).

Стек: **FastAPI + PostgreSQL + SQLAlchemy 2 + Alembic** · **React + TypeScript + Vite + TanStack Query + Recharts** · **Docker Compose**.

> Демонстрационные данные в seed **синтетические** и не являются производственными измерениями.

## Быстрый старт (Docker)

```bash
cd gno-monitor
cp .env.example .env
# при необходимости измените SECRET_KEY и ADMIN_PASSWORD
docker compose up --build
```

После запуска:

| Сервис | URL |
|--------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000/api/v1 |
| Swagger UI | http://localhost:8000/docs |
| Health | http://localhost:8000/health |

### Учётные записи (создаются seed при первом старте)

Пароли задаются в `.env` / seed (не храните их в git для production):

| Роль | Логин | Пароль по умолчанию |
|------|-------|---------------------|
| Администратор | `admin` | значение `ADMIN_PASSWORD` из `.env` (`ChangeMeAdmin123!`) |
| Технолог | `technologist` | `TechnoDemo123!` |
| Просмотр | `viewer` | `ViewerDemo123!` |

## Локальный запуск без Docker (кратко)

1. Поднимите PostgreSQL и задайте `DATABASE_URL`.
2. Backend:

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python -c "from app.db.session import SessionLocal; from app.db.seed import seed_database; db=SessionLocal(); print(seed_database(db)); db.close()"
uvicorn app.main:app --reload --port 8000
```

3. Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Миграции и seed

- Миграции Alembic: `backend/alembic/versions/001_initial_schema.py`
- При старте контейнера backend: ожидание БД → `alembic upgrade head` → uvicorn
- При `SEED_ON_STARTUP=true` выполняется идемпотентный seed и первичный прогон аналитики

## Аналитика

1. Isolation Forest — аномалии режима  
2. Random Forest Classifier — риск отказа на горизонте 7 суток (при достаточной разметке по истории отказов)  
3. Экспертно-статистический fallback, если RF не обучен  

Пороги риска и аномалий — в `.env` / `app/core/constants.py`. Оценка **не** выдаётся за промышленно калиброванную вероятность.

## Тесты

```bash
# backend
cd backend
pip install -r requirements.txt
pytest -q

# frontend
cd frontend
npm install
npm test
npm run build
```

## Структура

```
gno-monitor/
  backend/app/{api,core,db,models,schemas,repositories,services,analytics,tasks}
  frontend/src/{api,pages,features,components,layouts,routes}
  docker-compose.yml
  .env.example
```
