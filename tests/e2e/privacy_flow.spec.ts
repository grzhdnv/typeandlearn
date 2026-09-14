import { test, expect } from "@playwright/test";

test.describe("Account and Privacy Flow", () => {
  test("opens account modal, displays identity, exports data, and closes modal", async ({
    page,
  }) => {
    // 1. Navigate to home
    await page.goto("/");
    await expect(page.locator("nav")).toContainText("typeandlearn");

    // 2. Click Account button in top navigation
    const accountBtn = page.locator("#btn-account-nav");
    await expect(accountBtn).toBeVisible();
    await accountBtn.click();

    // 3. Verify Account modal is visible
    const accountModal = page.locator("#account-modal");
    await expect(accountModal).toBeVisible();
    await expect(page.locator("#account-modal-title")).toContainText("Account & Privacy");

    // 4. Verify owner identity is shown
    const ownerIdEl = page.locator("#profile-owner-id");
    await expect(ownerIdEl).toBeVisible();
    await expect(ownerIdEl).not.toBeEmpty();

    // 5. Test Data Export
    const exportBtn = page.locator("#btn-export-data");
    await expect(exportBtn).toBeVisible();

    // Intercept download event
    const downloadPromise = page.waitForEvent("download");
    await exportBtn.click();
    const download = await downloadPromise;

    expect(download.suggestedFilename()).toMatch(/^typeandlearn-export-.*\.json$/);

    // 6. Test Danger Zone confirmation UI (without actually purging everything in test run)
    const purgeBtn = page.locator("#btn-delete-account");
    await expect(purgeBtn).toBeVisible();
    await purgeBtn.click();

    const cancelPurgeBtn = page.locator("#btn-cancel-delete");
    await expect(cancelPurgeBtn).toBeVisible();
    await cancelPurgeBtn.click();
    await expect(purgeBtn).toBeVisible();

    // 7. Close modal
    const closeBtn = page.locator("#btn-close-account-modal");
    await closeBtn.click();
    await expect(accountModal).not.toBeVisible();
  });
});
