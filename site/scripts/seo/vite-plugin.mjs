// Vite plugin (build only) that
//   1. injects the Content-Security-Policy <meta> into index.html — build only,
//      because the dev server needs inline scripts for React Fast Refresh;
//   2. after the bundle is written, runs the SEO generator over dist/.
// Set NGJ_SITE_URL to build for another origin (canonicals, sitemap, og:image)
// and NGJ_SEO_DATA_DIR to read job data from somewhere other than public/
// (build:fixtures points it at test/fixtures).

import { resolve } from 'node:path';
import { DEFAULT_SITE_URL, generateSeo } from './generate.mjs';

/**
 * App CSP. Scripts: only our own bundle + GoatCounter's loader. Inline styles
 * are needed because the React views use style props. Connections: GitHub API
 * (contributors view) and the GoatCounter count endpoint.
 */
export const APP_CSP = [
  "default-src 'self'",
  "script-src 'self' https://gc.zgo.at",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: https://avatars.githubusercontent.com https://gc.zgo.at https://*.goatcounter.com",
  "connect-src 'self' https://api.github.com https://*.goatcounter.com",
  "font-src 'self'",
  "base-uri 'self'",
  "form-action 'none'",
  "object-src 'none'",
].join('; ');

const CHARSET_META = /<meta charset="[^"]*">/i;

/** Insert the CSP <meta> after <meta charset> (or at the start of <head>). */
export function injectCsp(html, csp) {
  const tag = `<meta http-equiv="Content-Security-Policy" content="${csp.replace(/"/g, '&quot;')}">`;
  if (CHARSET_META.test(html)) return html.replace(CHARSET_META, (m) => `${m}\n  ${tag}`);
  return html.replace(/<head>/i, (m) => `${m}\n  ${tag}`);
}

export function ngjSeo({
  siteUrl = process.env.NGJ_SITE_URL || DEFAULT_SITE_URL,
  dataDir = process.env.NGJ_SEO_DATA_DIR,
  csp = APP_CSP,
} = {}) {
  let config;
  return {
    name: 'ngj-seo',
    apply: 'build',
    configResolved(resolved) {
      config = resolved;
    },
    transformIndexHtml: {
      order: 'post',
      // Right after <meta charset>, ahead of every script/style it governs.
      handler(html) {
        return injectCsp(html, csp);
      },
    },
    async closeBundle() {
      if (!config || config.build.ssr) return;
      const distDir = resolve(config.root, config.build.outDir);
      const logger = config.logger;
      const log = { log: (m) => logger.info(m), warn: (m) => logger.warn(m) };
      const stats = await generateSeo({
        publicDir: dataDir ? resolve(config.root, dataDir) : config.publicDir, distDir, siteUrl, log,
      });
      const skipped = Object.entries(stats.jsonLdSkipped).map(([k, v]) => `${k}: ${v}`).join(', ');
      logger.info(
        `[seo] ${stats.jobPages} job pages (${stats.jsonLd} with JobPosting JSON-LD${skipped ? `; skipped — ${skipped}` : ''}), `
        + `${stats.landingPages} landing pages, ${stats.sitemapUrls} sitemap URLs, ${stats.prerendered} jobs prerendered into index.html`,
      );
    },
  };
}
