# Neural Math Assistant Frontend

Angular 22 single-page frontend for the async ML FastAPI chat service. It provides registration, login, token refresh, thread management, message history, and chat with the LangGraph assistant.

## Requirements

- Node.js 22 or newer
- npm
- The backend running at `http://localhost:8000` for local development

## Local development

From `frontend/`:

```bash
npm install
npm start
```

Open `http://localhost:4200`. The Angular dev server proxies `/api/*` to `http://localhost:8000` using `proxy.conf.json`, so frontend code uses the same `/api` base path in every environment.

Useful commands:

```bash
npm run build                 # production build
npm run watch                 # development watch build
npm start -- --port 4300     # use a different local port
```

## Frontend structure

- `src/app/login/`: login and registration screens
- `src/app/chat/`: thread list, message history, and chat interface
- `src/app/core/auth.service.ts`: login, registration, refresh, logout, and token storage
- `src/app/core/auth.interceptor.ts`: adds the bearer token and handles expired access tokens
- `src/app/services/chat.service.ts`: sends chat messages
- `src/app/services/thread.service.ts`: creates, lists, loads, and deletes threads
- `src/app/app.routes.ts`: application routes and authentication guard

Access and refresh tokens are stored in `localStorage` under `access_token` and `refresh_token`. The interceptor attaches the access token to protected requests and attempts a refresh when the API returns an unauthorized response.

## API calls

The services call these backend paths through `/api`:

| Service | Routes |
|---|---|
| Auth | `/auth/login`, `/auth/register`, `/auth/refresh`, `/auth/me` |
| Threads | `/threads`, `/threads/{thread_id}/messages`, `/threads/{thread_id}` |
| Chat | `/chat` |

The backend must allow the frontend origin through its `CORS_ORIGINS` setting. With the local proxy, use `CORS_ORIGINS=http://localhost:4200` in the backend environment.

## Docker and deployment

Build the production image from `frontend/`:

```bash
docker build -t mlfastapi-frontend .
docker run --rm -p 8080:8080 -e BACKEND_HOST=localhost mlfastapi-frontend
```

Nginx serves the compiled Angular application on port `8080` and proxies `/api/` to `http://${BACKEND_HOST}:8000/`. The Render Blueprint supplies `BACKEND_HOST` from the deployed API service.
