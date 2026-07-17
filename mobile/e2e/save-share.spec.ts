import { test, expect } from '@playwright/test';

test.describe('保存 / 分享 (web)', () => {
  test('cross-origin image downloads without leaving 8081', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('选择一款发型开始试戴')).toBeVisible();

    const imageUrl =
      'http://localhost:8000/api/comfyui/output/7dccd83bd1ea48fe95e26fba135eb0d6.png';

    // Probe that backend serves the sample result (skip if file missing)
    const probe = await page.request.get(imageUrl);
    test.skip(!probe.ok(), 'sample output image not available on :8000');

    const downloadPromise = page.waitForEvent('download', { timeout: 20_000 });

    await page.evaluate(async (url) => {
      // Same strategy as ActionButtons.downloadViaBlob
      const res = await fetch(url);
      if (!res.ok) throw new Error(`fetch ${res.status}`);
      const blob = await res.blob();
      const objectUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = objectUrl;
      a.download = 'hairstyle-result.png';
      a.rel = 'noopener';
      document.body.appendChild(a);
      a.click();
      a.remove();
    }, imageUrl);

    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/\.png$/i);

    // Must stay on the Expo web origin — old bug navigated to :8000
    expect(page.url()).toMatch(/localhost:8081/);
    await expect(page.getByText('选择一款发型开始试戴')).toBeVisible();
  });
});
