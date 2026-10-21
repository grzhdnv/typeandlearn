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


test("saved source stays visible while preparation waits and practice appears on polling", async ({ page, request }) => {
  const source = "Le petit chat dort. Il rêve.";
  const upload = await request.post("http://127.0.0.1:18000/texts", { data: { text: source, language: "French" } });
  expect(upload.ok()).toBe(true);
  const { id } = await upload.json();
  let preparing = true;
  await page.route(`**/api/texts/${id}`, async route => {
    const response = await route.fetch();
    const payload = await response.json();
    if (preparing) {
      payload.data = { ...payload.data, status: "processing", enrichment_stage: "preprocessing", original_paragraphs: [], total_sentences: 0, source_text: source };
    }
    await route.fulfill({ response, json: payload });
  });
  await page.goto(`/practice/${id}`);
  await expect(page.getByText("Preparing text for practice...", { exact: true })).toBeVisible();
  await expect(page.getByText("You can start typing the original text now", { exact: false })).not.toBeVisible();
  await page.getByText("View saved source", { exact: true }).click();
  await expect(page.locator("details")).toContainText(source);
  preparing = false;
  await expect(page.locator("#typing-canvas")).toContainText("Le petit chat dort.");
  await expect(page.getByText("Preparing text for practice...", { exact: true })).not.toBeVisible();
});


test("legacy null badges stay hidden and optional metadata can be cleared", async ({ page, request }) => {
  const upload = await request.post("http://127.0.0.1:18000/texts", {
    data: { text: "Hallo Welt. Das ist ein Test.", language: "German", title: "Metadata regression" },
  });
  expect(upload.ok()).toBe(true);
  const { id } = await upload.json();
  await page.route("**/api/texts/titles", async route => {
    const response = await route.fetch();
    const payload = await response.json();
    payload.titles = payload.titles.map((text: { id: string }) =>
      String(text.id) === String(id) ? { ...text, author: " undefined ", category: "null" } : text);
    await route.fulfill({ response, json: payload });
  });
  await page.goto("/");
  const card = page.locator(`.text-card-hover:has(a[href="/practice/${id}"])`);
  await expect(card).toBeVisible();
  await expect(card.getByText("null", { exact: true })).not.toBeVisible();
  await expect(card.getByText(/By.*undefined/)).not.toBeVisible();
  await card.getByTitle("Edit metadata", { exact: true }).click();
  await expect(card.getByPlaceholder("Author", { exact: true })).toHaveValue("");
  await expect(card.getByPlaceholder("Category", { exact: true })).toHaveValue("");
  await page.unroute("**/api/texts/titles");
  await card.getByPlaceholder("Author", { exact: true }).fill("Anna Null");
  await card.getByPlaceholder("Category", { exact: true }).fill("Null hypothesis");
  await card.getByTitle("Done editing", { exact: true }).click();
  await page.reload();
  await expect(card).toContainText("Anna Null");
  await expect(card).toContainText("Null hypothesis");
  await card.getByTitle("Edit metadata", { exact: true }).click();
  await card.getByPlaceholder("Author", { exact: true }).fill("");
  await card.getByPlaceholder("Category", { exact: true }).fill("");
  await card.getByTitle("Done editing", { exact: true }).click();
  await page.reload();
  await expect(card).not.toContainText("Anna Null");
  await expect(card).not.toContainText("Null hypothesis");
  const saved = await request.get(`http://127.0.0.1:18000/texts/${id}`);
  const { data } = await saved.json();
  expect(data.author).toBeNull();
  expect(data.category).toBeNull();
});
