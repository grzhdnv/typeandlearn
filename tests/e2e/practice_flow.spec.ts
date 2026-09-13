import { test, expect } from "@playwright/test";

test.describe("Intake and Practice Flow", () => {
  test("submits a new text, navigates to practice, types sentence, and completes drill", async ({
    page,
  }) => {
    // Auto-accept confirmation dialogs (e.g. for cleanup delete)
    page.on("dialog", async (dialog) => {
      await dialog.accept();
    });

    // 1. Navigate to library
    await page.goto("/");
    await expect(page.locator("nav")).toContainText("typeandlearn");

    // 2. Open Add Text form
    const addTextBtn = page.getByRole("button", { name: /add text/i });
    await expect(addTextBtn).toBeVisible();
    await addTextBtn.click();

    // 3. Fill in custom text form
    const uniqueTitle = `E2E Story ${Date.now()}`;
    await page.getByPlaceholder("Title (Optional)").fill(uniqueTitle);
    await page
      .getByPlaceholder("Paste new text here...")
      .fill("Hallo Welt. Das ist ein Test.");

    // Submit text
    const submitBtn = page.getByRole("button", { name: "SUBMIT" });
    await submitBtn.click();

    // 4. Wait for text card in library
    const textCard = page.locator("div.text-card-hover", {
      hasText: uniqueTitle,
    });
    await expect(textCard).toBeVisible({ timeout: 15000 });

    // 5. Navigate to practice page
    const practiceLink = textCard.getByRole("link", { name: /practice/i });
    await practiceLink.click();
    await expect(page).toHaveURL(/\/practice\/\d+/);

    // 6. Verify practice view rendered & wait for background processing to complete
    await expect(page.locator("h1")).toContainText(uniqueTitle);
    await expect(page.getByText(/Translating text with AI/i)).not.toBeVisible({
      timeout: 30000,
    });
    const typingCanvas = page.locator("#typing-canvas");
    await expect(typingCanvas).toBeVisible({ timeout: 10000 });

    // The first sentence should be "Hallo Welt."
    await expect(typingCanvas).toContainText("Hallo Welt.");

    // 7. Click to focus and start typing
    const hiddenInput = page.locator("#typing-hidden-input");
    await hiddenInput.focus();

    // Type the first sentence
    await page.keyboard.type("Hallo Welt.", { delay: 40 });

    // 8. Assert real-time metrics updated
    const metricWpm = page.locator("#metric-wpm");
    const metricAccuracy = page.locator("#metric-accuracy");
    await expect(metricWpm).not.toHaveText("--");
    await expect(metricAccuracy).not.toHaveText("--%");

    // 9. Assert post-session results modal appears
    const resultsModal = page.locator("#results-modal");
    await expect(resultsModal).toBeVisible({ timeout: 5000 });
    await expect(page.locator("#results-net-wpm")).toBeVisible();
    await expect(page.locator("#results-accuracy")).toHaveText("100%");
    await expect(page.locator("#results-mistakes")).toHaveText("0");

    // 10. Close results modal with Review button
    const reviewBtn = page.locator("#btn-results-review");
    await reviewBtn.click();
    await expect(resultsModal).not.toBeVisible();

    // 11. Cleanup: Return to library and delete the test text
    await page.goto("/");
    const cardToDelete = page.locator("div.text-card-hover", {
      hasText: uniqueTitle,
    });
    await expect(cardToDelete).toBeVisible();
    const deleteBtn = cardToDelete.getByTitle("Delete Text");
    await deleteBtn.click();
    await expect(cardToDelete).not.toBeVisible({ timeout: 10000 });
  });
});
