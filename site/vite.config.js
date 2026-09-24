import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { ngjSeo } from './scripts/seo/vite-plugin.mjs';

// `base: './'` keeps every emitted URL relative, so the build works both at the
// custom-domain root (jobs.riteshrana.engineer) and under a sub-path
// (username.github.io/New-Grad-Jobs/). Runtime data fetches use relative URLs
// for the same reason (see src/data/*).
export default defineConfig({
  base: './',
  // ngjSeo: build-time CSP meta + per-job pages, sitemap, robots, prerendered
  // job list (reads public/ data, tolerates it being absent).
  plugins: [react(), ngjSeo()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: false,
    // Never base64-inline font files: inlined subsets would bloat the
    // render-blocking CSS, while separate files are fetched only when the
    // page actually uses a glyph from that unicode-range.
    assetsInlineLimit: (filePath) => (/\.woff2?$/.test(filePath) ? false : undefined),
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.{js,jsx}', 'test/**/*.test.{js,jsx}'],
    coverage: {
      provider: 'v8',
      include: ['src/lib/**/*.js'],
      reporter: ['text', 'json-summary'],
      thresholds: {
        lines: 80,
      },
    },
  },
});
