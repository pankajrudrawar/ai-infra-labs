const { chromium } = require('playwright');
(async () => {
  const out = process.argv[2];
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
  await p.goto('file://' + require('path').resolve(__dirname, 'slides.html'));
  await p.evaluate(() => document.fonts.ready);
  const ids = ['s-title','s-summary','s-arch','s-steps','s-sizing','s-g1','s-g2','s-g3','s-g4','s-cost','s-next'];
  let n = 0;
  for (const id of ids) {
    if (id === 's-arch') {
      for (let k = 1; k <= 5; k++) {
        await p.evaluate(k => setStep(k), k);
        await p.locator('#'+id).screenshot({ path: `${out}/${String(++n).padStart(2,'0')}-${id}-${k}.png` });
      }
    } else {
      await p.locator('#'+id).screenshot({ path: `${out}/${String(++n).padStart(2,'0')}-${id}.png` });
    }
  }
  await b.close();
})();
