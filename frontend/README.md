# ThreadCraft — Frontend

React 19 + Vite. Plain JSX (no TypeScript — see `docs/architecture/adr/0004-plain-jsx-over-typescript.md`), no CSS framework: `src/index.css` is a hand-written design-token based system (cream/taupe/brown editorial palette, Cormorant Garamond + Jost).

## Develop

```bash
npm install
npm run dev       # http://localhost:5173, proxies /api to the backend
```

## Scripts

| Command | Does |
|---|---|
| `npm run dev` | Vite dev server with HMR |
| `npm run build` | Production build to `dist/` |
| `npm run preview` | Serve the production build locally |
| `npm run lint` | ESLint — enforced in CI |

## Structure

```
src/
├── App.jsx              # routes
├── components/          # Navbar, Footer, shared UI
├── pages/                # one file per route
└── index.css             # the whole design system
```

See the [root README](../README.md) for the full-stack picture.
