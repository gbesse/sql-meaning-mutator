import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
const port = 18766,
  base = `http://127.0.0.1:${port}`;
const server = spawn(
  process.env.PYTHON || 'python3',
  ['-m', 'sql_meaning', 'serve', String(port)],
  { stdio: ['ignore', 'pipe', 'inherit'] },
);
let browser;
try {
  for (let i = 0; i < 100; i++) {
    try {
      if ((await fetch(base)).ok) break;
    } catch {}
    if (server.exitCode !== null) throw Error('server exited');
    if (i === 99) throw Error('server timeout');
    await new Promise((r) => setTimeout(r, 100));
  }
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1300, height: 1000 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  for (const lang of ['fr', 'en', 'es']) {
    await page.goto(`${base}/?lang=${lang}`);
    await page.waitForFunction(() => document.getElementById('query').value.includes('JOIN lines'));
    assert.equal(await page.locator('html').getAttribute('lang'), lang);
    await page.locator('#search').click();
    await page.waitForFunction(() => document.getElementById('rows').textContent === '4');
    assert.match(await page.locator('#actual').textContent(), /4000/);
    assert.match(await page.locator('#expected').textContent(), /2000/);
    assert.equal(await page.locator('.witness-table').count(), 3);
    const event = page.waitForEvent('download');
    await page.locator('#download').click();
    assert.equal((await event).suggestedFilename(), 'sql-counterexample.json');
    await page.locator('#fix').click();
    await page.waitForFunction(() => document.getElementById('rows').textContent === '—');
    assert.match(
      await page.locator('#status').textContent(),
      { fr: /ne prouve/, en: /does not prove/, es: /no demuestra/ }[lang],
    );
    await page.locator('#query').fill('DELETE FROM customers');
    await page.locator('#search').click();
    await page.waitForFunction(() => !document.getElementById('search').disabled);
    assert.match(
      await page.locator('#verdict').textContent(),
      { fr: /INVALIDES/, en: /INVALID/, es: /NO VÁLIDOS/ }[lang],
    );
  }
  await page.goto(`${base}/?lang=fr`);
  await page.waitForFunction(() => document.getElementById('query').value.includes('JOIN lines'));
  await page.locator('#search').click();
  await page.waitForFunction(() => document.getElementById('rows').textContent === '4');
  await mkdir('.local', { recursive: true });
  await page.screenshot({ path: '.local/preview-fr.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  assert.deepEqual(errors, []);
  console.log(
    'FR/EN/ES: real SQLite witness, correction, read-only errors, export and mobile verified.',
  );
} finally {
  if (browser) await browser.close();
  server.kill('SIGTERM');
}
