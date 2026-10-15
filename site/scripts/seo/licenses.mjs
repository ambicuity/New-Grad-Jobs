// dist/third-party-licenses.txt: the full licence text of every third-party
// package whose code or font files ship in the site bundle. MIT and OFL-1.1
// both require their notice to travel with redistributed copies. Read from
// node_modules at build time so versions and texts never drift by hand.

import { readFile, readdir } from 'node:fs/promises';
import { join } from 'node:path';

/**
 * Packages bundled into dist/: package.json `dependencies` plus the runtime
 * packages they pull in. A test keeps this in step with package.json.
 */
export const BUNDLED_PACKAGES = Object.freeze([
  'react',
  'react-dom',
  'scheduler',
  '@tanstack/react-virtual',
  '@tanstack/virtual-core',
  '@fontsource/jetbrains-mono',
]);

const LICENSE_FILE_RE = /^(?:licen[cs]e|copying)(?:\.(?:md|txt))?$/i;
const RULE = '='.repeat(78);

async function readPackage(nodeModulesDir, name) {
  const dir = join(nodeModulesDir, name);
  const pkg = JSON.parse(await readFile(join(dir, 'package.json'), 'utf8'));
  const file = (await readdir(dir)).find((n) => LICENSE_FILE_RE.test(n));
  if (!file) throw new Error('no licence file');
  const license = typeof pkg.license === 'string' ? pkg.license : 'see text';
  return { version: pkg.version, license, text: (await readFile(join(dir, file), 'utf8')).trim() };
}

/**
 * @param {string} nodeModulesDir
 * @param {Pick<Console, 'warn'>} [log]
 * @param {readonly string[]} [packages]
 * @returns {Promise<string>}
 */
export async function renderThirdPartyLicenses(nodeModulesDir, log = console, packages = BUNDLED_PACKAGES) {
  const sections = [];
  for (const name of packages) {
    try {
      const { version, license, text } = await readPackage(nodeModulesDir, name);
      sections.push(`${name} ${version} — ${license}\n${RULE}\n${text}`);
    } catch (err) {
      log.warn(`[seo] third-party licence for ${name} not found: ${err.message}`);
      sections.push(`${name} — licence text not found at build time; see the package's own repository.`);
    }
  }
  return [
    'Third-party software bundled with NGJ (New Grad Jobs), https://jobs.riteshrana.engineer',
    'NGJ\'s own code is MIT licensed: https://github.com/ambicuity/New-Grad-Jobs/blob/main/LICENSE',
    'Job listings belong to the employers that published them and are not covered by any licence below.',
    '',
    ...sections.flatMap((s) => [s, '']),
  ].join('\n');
}
