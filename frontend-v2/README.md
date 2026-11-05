# TalentMatch Frontend V2

React + TypeScript + Vite frontend for the existing TalentMatch FastAPI backend.

Add this service under `services:` in the existing root `docker-compose.yml`; do not replace the existing services:

```yaml
  frontend:
    build:
      context: ./frontend-v2
      dockerfile: Dockerfile.dev
    ports:
      - "5173:5173"
    depends_on:
      - talentmatch
    volumes:
      - ./frontend-v2:/app
      - /app/node_modules
```

Run from the project root:

```powershell
docker compose up -d --build frontend
```

Open http://localhost:5173. Vite proxies `/api/...` requests to the `talentmatch` Compose service, so the browser does not need direct access to the internal Docker hostname.

The status endpoint must return `status`, and its completed record must contain `overall_score` and the saved result JSON. Confirm the exact saved `result` structure against the worker before relying on the result normalizer.
