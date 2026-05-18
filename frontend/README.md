# Frontend — Salary Management UI

React + Vite + Tailwind CSS v4, with [shadcn/ui](https://ui.shadcn.com/) components.

## Run locally

```bash
cd frontend
npm install
npm run dev
```

App: <http://localhost:5173>

## Adding shadcn components

```bash
npx shadcn@latest add <component>
# e.g. npx shadcn@latest add input card dialog
```

Components are copied into `src/components/ui/`. The `@/` alias resolves to `./src` (configured in `vite.config.js` and `jsconfig.json`).
