import { defineConfig } from 'vite';
import { execSync } from 'node:child_process';

// Build number appended to every data / model / texture / photo URL (src/util.js versioned()): GitHub Pages serves
// them with a 10-minute cache, so a new deploy would otherwise mix fresh code with stale assets for a while.
function buildId() {
  if (process.env.GITHUB_SHA) return process.env.GITHUB_SHA.slice(0, 8);
  try { return execSync('git rev-parse --short=8 HEAD', { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim(); } catch { /* not a git checkout */ }
  return Date.now().toString(36);
}

export default defineConfig(({ command }) => ({
  base: './',
  server: { port: 5197 },
  build: {
    chunkSizeWarningLimit: 2000,
    assetsInlineLimit: 0,
    // the game, the 새 소식 page (it shares src/notes.js with the game's news panel) and the 캠퍼스 사람들 page (the
    // cast alone, src/people.js)
    rollupOptions: { input: { main: 'index.html', news: 'news.html', people: 'people.html' } },
  },
  define: { __BUILD__: JSON.stringify(command === 'serve' ? 'dev' : buildId()) },
}));
