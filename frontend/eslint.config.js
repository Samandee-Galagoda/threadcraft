import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  // .vite is Vite's on-disk dependency cache — prebundled third-party code that
  // is neither ours nor lintable.
  globalIgnores(['dist', '.vite', 'node_modules']),
  {
    files: ['**/*.{js,jsx}'],
    extends: [
      js.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
  },
  {
    // Co-locating a context's provider with its consumer hook is the idiomatic
    // React pattern. Splitting them into separate files purely to satisfy the
    // fast-refresh heuristic would make the code worse, and fast refresh only
    // degrades to a full reload when these files change.
    files: ['src/context/**/*.jsx'],
    rules: { 'react-refresh/only-export-components': 'off' },
  },
])
