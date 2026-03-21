# Type and Learn

### MonkeyType for learning languages

## Run locally

Start the backend and frontend in separate terminals.

### 1. Start backend (FastAPI)

From the project root:

```bash
source .venv/bin/activate
fastapi dev backend/main.py
```

Backend runs at `http://127.0.0.1:8000`.

### 2. Start frontend (SolidJS + Vite)

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:3000`.

The frontend is configured to proxy `/api/*` requests to the backend during development.

## TODO

- [ ] Add database to store translations and user data.
- [ ] Implement user authentication.