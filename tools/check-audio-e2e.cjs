'use strict';
/*
 * Optional local integration check. No production request is allowed.
 * Start the local site on port18768 and the audio PHP test adapter on18769.
 * Set PLAYWRIGHT_MODULE to the installed playwright package and BROWSER_BIN
 * to a Chromium executable. All audio input is from an API-generated WAV,
 * supplied as a fake microphone: this is not a physical acoustic test.
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const site = process.env.AUDIO_TEST_SITE || 'http://127.0.0.1:18768';
const api = process.env.AUDIO_TEST_API || 'http://127.0.0.1:18769';
for (const url of [site, api]) assert.ok(['127.0.0.1', 'localhost', '[::1]'].includes(new URL(url).hostname), 'Only loopback test servers are permitted');
const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'aisense-audio-e2e-'));
const launch = { executablePath: process.env.BROWSER_BIN || undefined, headless: true };
const failures = [];

async function prepare(page) {
  page.on('pageerror', error => failures.push(error.message));
  await page.route('https://aisenseapi.com/**', async route => {
    const url = new URL(route.request().url());
    assert.ok(url.pathname.startsWith('/services/v1/audio_'));
    if (route.request().method() === 'OPTIONS') {
      return route.fulfill({ status: 204, headers: { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'content-type' } });
    }
    const response = await route.fetch({ url: api + url.pathname, timeout: 60000 });
    await route.fulfill({ response, headers: { ...response.headers(), 'Access-Control-Allow-Origin': '*' } });
  });
}

async function run(mode) {
  const text = mode === 'audible' ? '<b>Hello \u00e6\u00f8\u00e5</b>' : 'High-frequency test.';
  const sound = path.join(directory, mode + '.wav');
  const sender = await chromium.launch(launch);
  let bytes;
  try {
    const page = await sender.newPage();
    await prepare(page);
    await page.goto(site + '/free-public-api-audio-encode-api-endpoint.html#try');
    await page.locator('#audio-data').fill(text);
    await page.locator('#audio-mode').selectOption(mode);
    await page.getByRole('button', { name: 'Create sound', exact: true }).click();
    await page.locator('#audio-output').waitFor({ state: 'visible' });
    const pending = page.waitForEvent('download');
    await page.getByRole('link', { name: 'Download WAV', exact: true }).click();
    await (await pending).saveAs(sound);
    bytes = fs.readFileSync(sound);
    assert.equal(bytes.toString('ascii', 0, 4), 'RIFF');
    assert.equal(bytes.readUInt16LE(34), 16);
  } finally { await sender.close(); }

  const duration = bytes.readUInt32LE(40) / bytes.readUInt32LE(28);
  // The fake microphone loops its source. Add the quiet gap a user leaves
  // after playing the sound so the real browser auto-stop path can run.
  const padded = Buffer.concat([bytes, Buffer.alloc(bytes.readUInt32LE(28) * 2)]);
  padded.writeUInt32LE(padded.length - 8, 4);
  padded.writeUInt32LE(padded.length - 44, 40);
  fs.writeFileSync(sound, padded);
  const receiver = await chromium.launch({ ...launch, args: [
    '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream', '--use-file-for-fake-audio-capture=' + sound
  ] });
  try {
    const page = await receiver.newPage({ viewport: { width: 390, height: 844 } });
    await prepare(page);
    await page.goto(site + '/free-public-api-audio-decode-api-endpoint.html#try');
    await page.getByRole('button', { name: 'Start listening', exact: true }).click();
    await page.waitForFunction(() => document.querySelector('#audio-status').textContent.startsWith('Listening.'));
    await page.locator('#audio-output').waitFor({ state: 'visible', timeout: 60000 });
    assert.equal(await page.locator('#audio-result-text').textContent(), text);
    assert.equal(await page.locator('#audio-result-base64').textContent(), Buffer.from(text, 'utf8').toString('base64'));
    assert.equal(await page.locator('#audio-result-text b').count(), 0, 'Decoded HTML is text, never markup');
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    console.log('ok ' + mode + ': sender WAV -> browser microphone/worklet -> automatic stop -> decoder -> exact UTF-8, ' + duration.toFixed(2) + ' s audio');
  } finally { await receiver.close(); }
}

(async () => {
  try {
    await run('audible');
    await run('ultrasound');
    assert.deepEqual(failures, []);
    console.log('Audio browser integration: 2 modes passed. Physical devices remain untested.');
  } finally {
    // Delete only files created by this test in its own new temporary directory.
    for (const name of ['audible.wav', 'ultrasound.wav']) {
      const file = path.join(directory, name);
      if (fs.existsSync(file)) fs.unlinkSync(file);
    }
    fs.rmdirSync(directory);
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
