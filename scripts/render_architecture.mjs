/** Render the one editable Mermaid source using a pinned, task-local CLI cache.
 * App/Notebook use only the committed SVG/PNG; they never load Node or a CDN.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import crypto from 'node:crypto';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const version = '12.0.0';
const cache = path.join(root, 'build', 'mermaid-cli');
const packageRoot = path.join(cache, 'node_modules', '@mermaid-js', 'mermaid-cli');
const packageFile = path.join(packageRoot, 'package.json');
if (!fs.existsSync(packageFile)) {
  throw new Error(`Install the renderer cache first: npm install --prefix build/mermaid-cli --cache build/mermaid-npm-cache --no-audit --no-fund --save-exact @mermaid-js/mermaid-cli@${version}. Set PUPPETEER_SKIP_DOWNLOAD=true to reuse an installed browser.`);
}
const metadata = JSON.parse(fs.readFileSync(packageFile, 'utf8'));
if (metadata.version !== version) throw new Error(`Expected Mermaid CLI ${version}, found ${metadata.version}`);
const browserCandidates = [
  process.env.MERMAID_BROWSER_EXECUTABLE,
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/usr/bin/chromium', '/usr/bin/chromium-browser', '/usr/bin/google-chrome',
].filter(Boolean);
const browser = browserCandidates.find(candidate => fs.existsSync(candidate));
if (!browser) throw new Error('Set MERMAID_BROWSER_EXECUTABLE to a local Chrome/Chromium/Edge executable. No browser is downloaded by this renderer.');
const puppeteerFile = path.join(root, 'build', 'mermaid-puppeteer.json');
fs.writeFileSync(puppeteerFile, JSON.stringify({
  executablePath: browser, headless: true,
  args: ['--disable-background-networking', '--disable-component-update', '--disable-sync', '--no-first-run', '--no-default-browser-check'],
}, null, 2));
const source = path.join(root, 'docs', 'diagrams', 'bluebikes_flow.mmd');
const cli = path.resolve(packageRoot, metadata.bin.mmdc);
const outputs = ['svg', 'png'].map(extension => path.join(path.dirname(source), `bluebikes_flow.${extension}`));
for (const output of outputs) {
  const args = [cli, '--input', source, '--output', output, '--puppeteerConfigFile', puppeteerFile,
                '--backgroundColor', '#ffffff', '--size', '2400', '--scale', '2',
                '--svgId', 'bluebikes-flow', '--no-font-embed'];
  const result = spawnSync(process.execPath, args, { cwd: root, encoding: 'utf8', timeout: 120000, windowsHide: true });
  if (result.status !== 0) throw new Error(`Mermaid render failed: ${result.stderr || result.stdout || result.error}`);
}
const svg = fs.readFileSync(outputs[0], 'utf8');
if (/<script\b/i.test(svg) || /(?:href\s*=\s*["']https?:|url\(\s*["']?https?:|@import)/i.test(svg)) {
  throw new Error('Generated SVG contains an external asset or script; do not use it as the offline app image.');
}
if (/<foreignObject\b/i.test(svg)) {
  throw new Error('Use global htmlLabels:false in the canonical Mermaid source for portable plain-SVG text.');
}
const digest = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const evidence = {
  rendered_at_utc: new Date().toISOString(), mermaid_cli_version: version,
  source: path.relative(root, source).replaceAll('\\', '/'), source_sha256: digest(source),
  browser_executable: browser, renderer_cache: 'build/mermaid-cli (ignored)',
  external_assets_or_scripts: false,
  plain_svg_text_without_foreignObject: true,
  outputs: outputs.map(output => ({ path: path.relative(root, output).replaceAll('\\', '/'),
                                   bytes: fs.statSync(output).size, sha256: digest(output) })),
};
fs.writeFileSync(path.join(root, 'build', 'architecture-render.json'), JSON.stringify(evidence, null, 2));
console.log(JSON.stringify(evidence, null, 2));
