import { test, expect } from "@playwright/test";

test("offline intake, metadata save, reload, and deletion", async ({ page }) => {
  page.on("dialog", dialog => dialog.accept());
  await page.goto("/");
  await page.getByRole("button", { name: "Add Text", exact: true }).click();
  await page.getByLabel("Text language", { exact: true }).selectOption("French");
  await page.getByLabel("Source text", { exact: true }).fill("Le petit chat dort. Il rêve.");
  const [upload] = await Promise.all([
    page.waitForResponse(response => response.url().endsWith("/api/texts") && response.request().method() === "POST"),
    page.getByRole("button", { name: "SUBMIT", exact: true }).click(),
  ]);
  expect(upload.ok()).toBe(true);
  const id = (await upload.json()).id;
  const card = page.locator(`.text-card-hover:has(a[href="/practice/${id}"])`);
  await expect(card).toBeVisible();
  await card.getByTitle("Edit metadata", { exact: true }).click();
  await card.getByPlaceholder("Title", { exact: true }).fill("French garden");
  await card.getByPlaceholder("Author", { exact: true }).fill("Test author");
  await card.getByPlaceholder("Category", { exact: true }).fill("Short story");
  await card.getByTitle("Done editing", { exact: true }).click();
  await expect(card.getByRole("heading", { name: "French garden" })).toBeVisible();
  await page.reload();
  await expect(card).toContainText("Test author");
  await expect(card).toContainText("Short story");
  await card.getByRole("link", { name: /Practice text/ }).click();
  await expect(page.locator("#typing-canvas")).toContainText("Le petit chat dort.");
  await expect(page.getByText("AI Enrichment Failed", { exact: true })).toBeVisible();
  await page.goto("/");
  await card.getByTitle("Delete Text", { exact: true }).click();
  await expect(card).not.toBeVisible();
});

test("automatic detection without AI gives an actionable error and preserves the text", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Add Text", exact: true }).click();
  await page.getByLabel("Source text", { exact: true }).fill("Hallo Welt.");
  await page.getByRole("button", { name: "SUBMIT", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Choose German");
  await expect(page.getByLabel("Source text", { exact: true })).toHaveValue("Hallo Welt.");
  await expect(page.getByRole("button", { name: "SUBMIT", exact: true })).toBeEnabled();
});
