# CamerHits frontend

React + TypeScript + Vite frontend for CamerHits. Authentication, song uploads, broadcasts, and event management use the FastAPI backend.

## Setup

```bash
npm install
copy .env.example .env.local
npm run dev
```

By default, the Vite dev server proxies API requests to `http://127.0.0.1:8000`. Set `VITE_API_PROXY_TARGET` in `.env.local` if the backend is elsewhere. For a separately hosted frontend, set `VITE_API_BASE_URL` to the backend origin and configure the backend's `CORS_ORIGINS` as a comma-separated list of allowed frontend origins.

## Scripts

- `npm run dev` starts the Vite development server.
- `npm run lint` checks TypeScript and React source files.
- `npm run build` type-checks and creates a production build.
- `npm run check` runs linting and the production build together.
