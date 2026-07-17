import { test, expect } from '@playwright/test';

test.describe('发型试戴 web UI', () => {
  test('home loads catalog and category filters', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('选择一款发型开始试戴')).toBeVisible();
    await expect(page.getByRole('button', { name: '筛选全部' })).toBeVisible();
    await expect(page.getByRole('button', { name: /选择发型：/ }).first()).toBeVisible({
      timeout: 20_000,
    });

    await page.getByRole('button', { name: '筛选男士' }).click();
    await expect(page.getByRole('button', { name: /选择发型：/ }).first()).toBeVisible();

    await page.getByRole('button', { name: '筛选女士' }).click();
    await expect(page.getByRole('button', { name: /选择发型：/ }).first()).toBeVisible();
  });

  test('tabs switch without stacking inactive screens', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('选择一款发型开始试戴')).toBeVisible();

    await page.getByRole('tab', { name: '我的效果' }).click();
    await expect(page).toHaveURL(/\/history/);
    await expect(page.getByText('还没有试戴记录')).toBeVisible();
    // Catalog must unmount so it cannot intercept clicks under history
    await expect(page.getByText('选择一款发型开始试戴')).toHaveCount(0);
    await expect(page.getByRole('button', { name: /选择发型：/ })).toHaveCount(0);

    await page.getByRole('button', { name: '去选发型' }).click();
    await expect(page).toHaveURL(/\/?$/);
    await expect(page.getByText('选择一款发型开始试戴')).toBeVisible();
    await expect(page.getByText('还没有试戴记录')).toHaveCount(0);
  });

  test('template card opens capture screen', async ({ page }) => {
    await page.goto('/');
    const card = page.getByRole('button', { name: /选择发型：/ }).first();
    await expect(card).toBeVisible({ timeout: 20_000 });
    await card.click();

    await expect(page.getByText('上传正面头像')).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/将试戴：|请使用清晰正面照/)).toBeVisible();
  });
});
