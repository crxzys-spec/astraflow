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

## 前端结构速览

- `src/App.tsx` 路由入口，封装 `RequireAuth` 与布局 `AppShell`。
- `src/services/*` 领域 API 调用封装（基于 OpenAPI 生成的 `src/client`）。
- `src/api/*` axios 配置、请求包装（去重/重试/错误归一化）。
- `src/store/*` Zustand 状态切片（runs/workflows/workflowPackages 等），`store/index.ts` 统一出口。
- `src/hooks/*` 业务 hooks，桥接 store 与 services。
- `src/pages/*` 业务页面；`src/components/*` 复用 UI/布局。
- `src/lib/sse/*` 事件流连接与分发；`src/styles/*` 全局样式入口。

### 路径别名

已在 `tsconfig.app.json` 与 `vite.config.ts` 配置：

- `@api` → `src/api`
- `@services` → `src/services`
- `@store` → `src/store`
- `@hooks` → `src/hooks`
- `@components` → `src/components`
- `@pages` → `src/pages`
- `@lib` → `src/lib`
- `@types` → `src/types`

后续可逐步将相对路径替换为别名，减少重构成本。
