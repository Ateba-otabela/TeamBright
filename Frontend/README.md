# Bantu Music 2.0 frontend

The frontend is a React + TypeScript + Vite application organized by application concerns and product features.

## Setup

```bash
npm install
copy .env.example .env.local
npm run dev
```

The API client reads `VITE_API_BASE_URL` and is ready to connect to the separate FastAPI service. Feature modules are intentionally structural only until their product requirements are defined.

## Scripts

- `npm run dev` starts the Vite development server.
- `npm run lint` checks TypeScript and React source files.
- `npm run build` type-checks and creates a production build.
- `npm run check` runs linting and the production build together.
