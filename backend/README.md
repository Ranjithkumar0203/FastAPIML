# ML FastAPI Backend

Async FastAPI backend for the Neural Math Assistant. It provides JWT authentication, thread and message persistence, and an async LangGraph agent with PostgreSQL checkpointing.

## Requirements

- Python 3.11 or newer
- PostgreSQL
- A Hugging Face token and an available chat model

## Configuration

Create `backend/.env` with the following values:

```env
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/app
POSTGRES_URL=postgresql://user:password@localhost:5432/app
JWT_SECRET=replace-with-a-long-random-secret
HF_Token=your-hugging-face-token
HF_MODEL=Qwen/Qwen3-Next-80B-A3B-Instruct
HF_PROVIDER=hf-inference
CORS_ORIGINS=http://localhost:4200
```

`DATABASE_URL` is used by async SQLAlchemy for application tables. `POSTGRES_URL` is used by LangGraph's `AsyncPostgresSaver`; both URLs may point to the same database. `JWT_ALGORITHM`, `JWT_EXPIRE_MINUTES`, and `JWT_REFRESH_EXPIRE_DAYS` are optional and have defaults in `auth.py`.

## Local development

From `backend/`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn main:app --reload
```

The API is available at `http://localhost:8000`. FastAPI's interactive documentation is available at `/docs`.

The application lifespan initializes the agent, creates the application tables with async SQLAlchemy, initializes LangGraph checkpoint tables, and compiles the graph before serving requests.

## API routes

| Method | Route | Auth | Description |
|---|---|---:|---|
| `GET` | `/` | No | Health-style response |
| `POST` | `/auth/register` | No | Register and return access/refresh tokens |
| `POST` | `/auth/login` | No | Login and return access/refresh tokens |
| `POST` | `/auth/refresh` | No | Rotate the token pair |
| `GET` | `/auth/me` | Yes | Return the current user |
| `POST` | `/threads` | Yes | Create a chat thread |
| `GET` | `/threads` | Yes | List the current user's threads |
| `GET` | `/threads/{thread_id}/messages` | Yes | Load thread messages |
| `POST` | `/chat` | Yes | Run the agent and save the conversation |
| `DELETE` | `/threads/{thread_id}` | Yes | Delete an owned thread |

Protected requests must send:

```http
Authorization: Bearer <access-token>
```

Example chat payload:

```json
{
	"thread_id": "thread-id",
	"message": "Calculate ReLU(-5)"
}
```

## Docker

```powershell
docker build -t mlfastapi-backend .
docker run --env-file .env -p 8000:8000 mlfastapi-backend
```

The container listens on `PORT` when provided, otherwise port `8000`.
