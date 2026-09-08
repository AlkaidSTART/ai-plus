import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const outDir = '/tmp/header-screenshots';
if (!fs.existsSync(outDir)) {
  fs.mkdirSync(outDir, { recursive: true });
}

const viewports = [
  { name: 'ultrawide', width: 1920, height: 1080 },
  { name: 'desktop', width: 1280, height: 800 },
  { name: 'laptop', width: 1024, height: 768 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'mobile', width: 375, height: 667 },
];

const locales = ['zh', 'en', 'id', 'th'];

(async () => {
  const browser = await chromium.launch();
  
  for (const vp of viewports) {
    for (const loc of locales) {
      const page = await browser.newPage({ viewport: { width: vp.width, height: vp.height } });
      await page.goto('http://localhost:5174');
      
      // Set localStorage locale
      await page.evaluate((l) => {
        localStorage.setItem('insightx_locale', l);
      }, loc);
      await page.reload();

      // Click enter button to enter workspace
      const enterBtn = page.locator('button.ln-btn-primary').first();
      if (await enterBtn.isVisible()) {
        await enterBtn.click();
      }

      await page.waitForSelector('header');
      await page.waitForTimeout(500);

      const header = page.locator('header');
      const filename = path.join(outDir, `header-${vp.name}-${loc}.png`);
      await header.screenshot({ path: filename });
      await page.close();
    }
  }

  // Also test mobile marketplace dropdown
  const page = await browser.newPage({ viewport: { width: 375, height: 667 } });
  await page.goto('http://localhost:5174');
  const enterBtn = page.locator('button.ln-btn-primary').first();
  if (await enterBtn.isVisible()) {
    await enterBtn.click();
  }
  await page.waitForSelector('header');
  await page.waitForTimeout(500);

  // Click mobile marketplace button
  const mpBtn = page.locator('header [data-dropdown]').nth(2).locator('button');
  if (await mpBtn.isVisible()) {
    await mpBtn.click();
    await page.waitForTimeout(200);
    await page.screenshot({ path: path.join(outDir, 'header-mobile-mp-dropdown.png') });
  }

  await browser.close();
  console.log('All screenshots completed.');
})();
