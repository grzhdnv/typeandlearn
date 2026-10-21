import { test, expect } from "@playwright/test";

test.describe("WCAG 2.1 AA Accessibility & Keyboard-Only Navigation", () => {
  test("keyboard navigation: skip link, top nav, and modal interaction", async ({
    page,
  }) => {
    // 1. Load library page
    await page.goto("/");
    await expect(page.locator("nav")).toContainText("typeandlearn");

    // 2. Tab to skip link
    await page.keyboard.press("Tab");
    const skipLink = page.getByRole("link", { name: /skip to main content/i });
    await expect(skipLink).toBeFocused();

    // 3. Activate skip link and verify focus moves to #main-content
    await page.keyboard.press("Enter");
    const mainContent = page.locator("#main-content");
    await expect(mainContent).toBeFocused();

    // 4. Navigate into top bar using Tab
    await page.locator("#btn-account-nav").focus();
    await expect(page.locator("#btn-account-nav")).toBeFocused();

    // 5. Open Account modal via keyboard Enter
    await page.keyboard.press("Enter");
    const accountModal = page.locator("#account-modal");
    await expect(accountModal).toBeVisible();

    // 6. Close Account modal using Escape key
    await page.keyboard.press("Escape");
    await expect(accountModal).not.toBeVisible();
  });

  test("landmarks, accessible roles, and screen reader live regions", async ({
    page,
  }) => {
    // 1. Verify single main landmark and labeled navigation landmark
    await page.goto("/");
    const nav = page.locator('nav[aria-label="Main Navigation"]');
    await expect(nav).toBeVisible();

    const main = page.locator("main#main-content");
    await expect(main).toBeVisible();

    // 2. Check input and button accessibility in library controls
    const searchInput = page.getByLabel(/search library texts/i);
    await expect(searchInput).toBeVisible();

    const addTextBtn = page.getByRole("button", { name: /add text/i });
    await expect(addTextBtn).toHaveAttribute("aria-expanded", "false");

    await addTextBtn.click();
    await expect(addTextBtn).toHaveAttribute("aria-expanded", "true");

    await expect(
      page.getByText(/detected automatically/i)
    ).toBeVisible();

    const textInput = page.getByPlaceholder(/paste new text here/i);
    await expect(textInput).toBeVisible();
  });

  test("practice session screen reader announcements and modal dialog semantics", async ({
    page,
  }) => {
    // Auto-accept confirmation dialogs
    page.on("dialog", async (dialog) => {
      await dialog.accept();
    });

    // 1. Submit a short test text for practice
    await page.goto("/");
    const addTextBtn = page.getByRole("button", { name: /add text/i });
    await addTextBtn.click();

    await page.getByPlaceholder("Paste new text here...").fill("Hallo Welt.");
    await page.getByLabel("Text language", { exact: true }).selectOption("German");
    const [uploadResponse] = await Promise.all([
      page.waitForResponse(
        (response) => response.url().endsWith("/texts") && response.request().method() === "POST"
      ),
      page.getByRole("button", { name: "SUBMIT" }).click(),
    ]);
    const textId = (await uploadResponse.json()).id as number;
    const practiceHref = `/practice/${textId}`;

    // Metadata is inferred by the LLM, so locate the new card by its practice link
    const textCard = page.locator(`div.text-card-hover:has(a[href="${practiceHref}"])`);
    await expect(textCard).toBeVisible({ timeout: 30000 });

    // 2. Navigate to practice
    const practiceLink = textCard.getByRole("link", { name: /practice/i });
    await practiceLink.click();
    await expect(page).toHaveURL(/\/practice\/\d+/);

    // 3. Verify screen reader live status region exists with aria-live="polite"
    const srStatus = page.locator("#sr-practice-status");
    await expect(srStatus).toBeAttached();
    await expect(srStatus).toHaveAttribute("role", "status");
    await expect(srStatus).toHaveAttribute("aria-live", "polite");

    // 4. Focus typing canvas and complete drill
    const hiddenInput = page.locator("#typing-hidden-input");
    await hiddenInput.focus();
    await page.keyboard.type("Hallo Welt.", { delay: 35 });

    // 5. Assert live region announced completion
    await expect(srStatus).toContainText(/drill completed/i);

    // 6. Verify results modal has accessible dialog semantics
    const resultsModal = page.locator("#results-modal");
    await expect(resultsModal).toBeVisible();
    await expect(resultsModal).toHaveAttribute("role", "dialog");
    await expect(resultsModal).toHaveAttribute("aria-modal", "true");

    // Close results modal via keyboard Escape
    await page.keyboard.press("Escape");
    await expect(resultsModal).not.toBeVisible();

    // Cleanup text
    await page.goto("/");
    const cardToDelete = page.locator(`div.text-card-hover:has(a[href="${practiceHref}"])`);
    await cardToDelete.getByTitle("Delete Text").click();
    await expect(cardToDelete).not.toBeVisible({ timeout: 10000 });
  });
});


test("mobile navigation and library controls stay available", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page).toHaveTitle("TypeAndLearn");
  await expect(page.getByRole("link", { name: "Library", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Analytics", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Add Text", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
