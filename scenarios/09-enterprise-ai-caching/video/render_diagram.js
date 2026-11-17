// Renders architecture.html to ../architecture-diagram.png (needs Node + Playwright).
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
  await p.goto('file://' + path.resolve(__dirname, 'architecture.html'));
  await p.evaluate(() => document.fonts.ready);
  await p.locator('#diagram').screenshot({ path: path.resolve(__dirname, '..', 'architecture-diagram.png') });
  await b.close();
})();
