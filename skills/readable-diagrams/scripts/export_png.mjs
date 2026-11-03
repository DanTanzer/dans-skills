// Photographs each figure of a figlib page as a PNG, with the arrow legend inside the picture.
//   node export_png.mjs /path/to/figures.html /path/to/out-folder [light|dark]
// The theme defaults to light. A dark export names each file NAME-dark.png.
// Uses the Chrome already installed on the Mac (or CHROME_PATH), so no browser download is needed.
// The page uses Arial and Menlo, which every Mac has, so the export needs no network.
import puppeteer from 'puppeteer';
import fs from 'node:fs';
import path from 'node:path';

const CHROME = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const [htmlPath, outDir, theme = 'light'] = process.argv.slice(2);
if (!htmlPath || !outDir) throw new Error('usage: node export_png.mjs HTML OUT_DIR [light|dark]');
if (!['light', 'dark'].includes(theme)) throw new Error('theme must be light or dark, got ' + theme);
if (!fs.existsSync(CHROME)) throw new Error('Chrome not found at ' + CHROME + '; set CHROME_PATH');
const suffix = theme === 'dark' ? '-dark' : '';
fs.mkdirSync(outDir, { recursive: true });

const browser = await puppeteer.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox', '--disable-gpu'] });
try {
  const page = await browser.newPage();
  await page.setViewport({ width: 1000, height: 900, deviceScaleFactor: 2 });
  await page.emulateMediaFeatures([{ name: 'prefers-color-scheme', value: theme }]);
  await page.goto('file://' + path.resolve(htmlPath), { waitUntil: 'networkidle0' });
  await page.evaluate(() => document.fonts.ready);

  // The page must really be in the asked theme: read one token back.
  const surface = await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--surface').trim().toUpperCase());
  const expected = theme === 'dark' ? '#141C26' : '#FFFFFF';
  if (surface !== expected) throw new Error(`theme ${theme}: --surface is ${surface}, expected ${expected}`);
  console.log('theme:', theme, '--surface', surface);

  const names = await page.evaluate(() => [...document.querySelectorAll('figure[data-png]')].map((f) => f.dataset.png));
  for (const [i, name] of names.entries()) {
    // One card per figure: the legend entries this figure uses, then its svg (moved, so marker ids stay unique).
    await page.evaluate((i) => {
      const figure = [...document.querySelectorAll('figure[data-png]')][i];
      const svg = figure.querySelector('svg');
      const legend = document.querySelector('.legend').cloneNode(true);
      const entries = [...legend.children];
      ['file', 'ring', 'say', 'loc'].forEach((kind, k) => {
        if (!svg.querySelector('.a-' + kind)) entries[k].remove();
      });
      legend.style.cssText = 'margin:0;padding:14px 18px 6px;font-size:14px;gap:6px 18px;';
      svg.style.cssText = 'display:block;width:calc(100% - 20px);margin:0 10px 10px;min-width:0;height:auto;';
      const card = document.createElement('div');
      card.id = 'png-card';
      card.style.cssText = 'width:920px;box-sizing:border-box;background:var(--surface);border:1px solid var(--line);border-radius:10px;overflow:hidden;';
      card.append(legend, svg);
      document.documentElement.style.background = 'transparent';
      document.body.style.cssText = 'margin:0;padding:0;background:transparent;';
      document.querySelector('.wrap').style.display = 'none';
      document.body.append(card);
    }, i);
    const card = await page.$('#png-card');
    const file = path.join(outDir, name + suffix + '.png');
    await card.screenshot({ path: file, omitBackground: true });
    await page.evaluate(() => document.getElementById('png-card').remove());
    console.log('wrote', file, fs.statSync(file).size, 'bytes');
  }
} finally {
  await browser.close();
}
