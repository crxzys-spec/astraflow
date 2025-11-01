# AstraFlow Dashboard

## Prerequisites

- Node.js 20+
- npm 10+
- Running scheduler API (configure `VITE_API_BASE_URL`)

## Setup

```bash
npm install
npm run generate:api
```

## Development Server

```bash
npm run dev -- --host
```

Visit `http://<your-ip>:5173` from other machines on the LAN.

## Environment

Create `.env.local` (or `.env.development`) with:

```
VITE_API_BASE_URL=https://scheduler.example.com
```

## Regenerating API Client

Whenever `docs/api/v1/openapi.yaml` changes:

```bash
npm run generate:api
```

Generated files live in `src/api/` and are git-ignored.
