import { test, expect } from "@playwright/test";

const inProgressStory = {
  id: 1,
  title: "Refetch Regression Story",
  status: "processing",
  language: "german",
  difficulty_level: "Unrated",
  word_count: 2,
  completed_sentences: 0,
  total_sentences: 1,
  estimated_time_minutes: 1,
  original_paragraphs: [
    {
      index: 0,
      sentences: [
        {
          index: 0,
          text: "Hallo Welt.",
          translation: "Hello World.",
          translation_hints: [],
        },
      ],
    },
  ],
  practice_sentences: [],
  top_words: [],
  enrichment_stage: "translating",
};

test.describe("Typing engine resilience", () => {
  test("typed progress survives background story refetches", async ({ page }) => {
    let storyFetches = 0;
    await page.route(/\/api\/texts\/1$/, async (route) => {
      storyFetches += 1;
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ message: "ok", data: inProgressStory }),
      });
    });

    await page.goto("/practice/1");

    const canvas = page.locator("#typing-canvas");
    await expect(canvas).toContainText("Hallo Welt.");

    const hiddenInput = page.locator("#typing-hidden-input");
    await hiddenInput.focus();
    await page.keyboard.type("Hallo", { delay: 30 });
    await expect(canvas.locator("span.text-completed")).toHaveCount(5);

    // The page polls while enrichment is active; wait for a refetch to land.
    await expect.poll(() => storyFetches).toBeGreaterThan(1);
    await page.waitForTimeout(200);

    await expect(canvas.locator("span.text-completed")).toHaveCount(5);
  });
});

// Keep these flows deterministic: provider work is represented by story refetches.
async function openStory(page: import("@playwright/test").Page, sentences = ["Hallo Welt.", "Hallo Welt."], generated = ["Test."]) {
  const story = {
    ...inProgressStory,
    status: "processed",
    enrichment_stage: "completed",
    total_sentences: sentences.length,
    original_paragraphs: [{ index: 0, sentences: sentences.map((text, index) => ({
      index, text, translation: "", translation_hints: [],
    })) }],
    practice_sentences: generated.map((sentence, index) => ({ index, sentence, translation: "", translation_hints: [] })),
  };
  await page.route(/\/api\/texts\/1$/, route => route.fulfill({ json: { data: story } }));
  await page.route(/\/api\/analytics\/sessions$/, route => route.fulfill({ json: {} }));
  await page.route(/\/api\/texts\/1\/progress$/, route => route.fulfill({ json: { completed_sentences: 1 } }));
  await page.goto("/practice/1");
  await expect(page.locator("#typing-canvas")).toContainText(sentences[0]);
  await page.locator("#typing-hidden-input").focus();
}

test("keyboard navigation resets identical sentences", async ({ page }) => {
  await openStory(page);
  await page.keyboard.type("Hallo");
  await expect(page.locator("span.text-completed")).toHaveCount(5);
  const next = page.getByRole("button", { name: /^Next/ });
  await next.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByText("Sentence 2 of 2", { exact: true })).toBeVisible();
  await expect(page.locator("span.text-completed")).toHaveCount(0);
  await page.keyboard.type("Hallo Welt.");
  await expect(page.locator("#results-modal")).toBeVisible();
});

test("resetting the first sentence clears typing and metrics", async ({ page }) => {
  await openStory(page);
  await page.keyboard.type("Hallo");
  await page.route(/\/api\/texts\/1\/reset$/, route => route.fulfill({ json: { completed_sentences: 0 } }));
  page.on("dialog", dialog => dialog.accept());
  await page.getByTitle("Reset Progress", { exact: true }).click();
  await expect(page.locator("span.text-completed")).toHaveCount(0);
  await expect(page.locator("#metric-wpm")).toHaveText("--");
  await expect(page.locator("#typing-hidden-input")).toBeFocused();
});

test("brackets in source text can be typed", async ({ page }) => {
  await openStory(page, ["[Hallo]"]);
  await page.keyboard.type("[Hallo]");
  await expect(page.locator("#results-modal")).toBeVisible();
  await expect(page.locator("#results-accuracy")).toHaveText("100%");
  await expect(page.getByText("Sentence 1 of 1", { exact: true })).toBeVisible();
});

test("generated drills do not mark original sentences completed", async ({ page }) => {
  let progressRequests = 0;
  await openStory(page);
  await page.route(/\/api\/texts\/1\/progress$/, route => {
    progressRequests += 1;
    return route.fulfill({ json: { completed_sentences: 1 } });
  });
  const generated = page.getByRole("button", { name: "Generated", exact: true });
  await generated.focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("#typing-canvas")).toContainText("Test.");
  await page.locator("#typing-hidden-input").focus();
  await page.keyboard.type("Test.");
  await expect(page.locator("#results-modal")).toBeVisible();
  expect(progressRequests).toBe(0);
});


test("reopening a story resumes the first unfinished original sentence", async ({ page }) => {
  await page.route(/\/api\/texts\/1$/, route => route.fulfill({ json: { data: {
    ...inProgressStory,
    status: "processed", enrichment_stage: "completed", total_sentences: 2,
    completed_sentences: 1, completed_sentence_indices: [0],
    original_paragraphs: [{ index: 0, sentences: [
      { index: 0, text: "First.", translation: "", translation_hints: [] },
      { index: 1, text: "Second.", translation: "", translation_hints: [] },
    ] }],
  } } }));
  await page.goto("/practice/1");
  await expect(page.locator("#typing-canvas")).toContainText("Second.");
  await expect(page.getByText("Sentence 2 of 2", { exact: true })).toBeVisible();
});

test("backend failures leave a usable error page", async ({ page }) => {
  await page.route(/\/api\/texts\/titles$/, route => route.fulfill({ status: 503, json: { detail: "Backend unavailable" } }));
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Unable to load this page" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  await expect(page.getByRole("navigation")).toBeVisible();
});


test("practice controls fit a phone viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openStory(page);
  await expect(page.getByRole("button", { name: /^Next/ })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});


test("results respect button activation and finish the final sentence", async ({ page }) => {
  await openStory(page, ["Hi."]);
  await page.keyboard.type("Hi.");
  await expect(page.locator("#btn-results-review")).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.locator("#btn-results-next")).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.locator("#btn-results-review")).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#results-modal")).not.toBeVisible();
  await expect(page).toHaveURL(/\/practice\/1$/);
  await page.locator("#typing-hidden-input").press("Escape");
  await page.keyboard.type("Hi.");
  await expect(page.locator("#results-modal")).toBeVisible();
  await page.locator("#btn-results-next").click();
  await expect(page).toHaveURL("/");
});


test("completion automatically advances identical sentences and saves each result once", async ({ page }) => {
  await openStory(page);
  const sessions: { sentence_index: number; accuracy: number }[] = [];
  const progress: number[] = [];
  await page.route(/\/api\/analytics\/sessions$/, route => {
    sessions.push(route.request().postDataJSON());
    return route.fulfill({ json: {} });
  });
  await page.route(/\/api\/texts\/1\/progress$/, route => {
    progress.push(route.request().postDataJSON().sentence_index);
    return route.fulfill({ json: { completed_sentences: progress.length } });
  });
  await page.keyboard.type("Hallo Welt.");
  await expect(page.getByText("Sentence 2 of 2", { exact: true })).toBeVisible();
  await expect(page.locator("#results-modal")).not.toBeVisible();
  await expect(page.locator("span.text-completed")).toHaveCount(0);
  await expect(page.locator("#typing-hidden-input")).toBeFocused();
  await page.keyboard.type("Hallo Welt.");
  await expect(page.locator("#results-modal")).toBeVisible();
  await expect.poll(() => sessions.length).toBe(2);
  await expect.poll(() => progress.length).toBe(2);
  expect(sessions.map(session => session.sentence_index)).toEqual([0, 1]);
  expect(sessions.map(session => session.accuracy)).toEqual([100, 100]);
  expect(progress).toEqual([0, 1]);
});

test("bracket shortcuts navigate while typing without inserting errors", async ({ page }) => {
  await openStory(page, ["First.", "Second.", "Third."]);
  await page.keyboard.type("Fi");
  await page.keyboard.press("[");
  await expect(page.locator("span.text-completed")).toHaveCount(2);
  await page.keyboard.press("]");
  await expect(page.getByText("Sentence 2 of 3", { exact: true })).toBeVisible();
  await expect(page.locator("span.text-completed")).toHaveCount(0);
  await expect(page.locator("#typing-hidden-input")).toBeFocused();
  await page.keyboard.type("Se");
  await page.keyboard.press("[");
  await expect(page.getByText("Sentence 1 of 3", { exact: true })).toBeVisible();
  await expect(page.locator("span.text-error")).toHaveCount(0);
  await page.keyboard.down("]");
  await page.keyboard.down("]");
  await page.keyboard.up("]");
  await expect(page.getByText("Sentence 2 of 3", { exact: true })).toBeVisible();
  await page.keyboard.press("]");
  await page.keyboard.press("]");
  await expect(page.getByText("Sentence 3 of 3", { exact: true })).toBeVisible();
  await expect(page.locator("span.text-error")).toHaveCount(0);
});

test("generated sentences also advance automatically", async ({ page }) => {
  await openStory(page, ["Original."], ["One.", "Two."]);
  await page.getByRole("button", { name: "Generated", exact: true }).click();
  await page.locator("#typing-hidden-input").focus();
  await page.keyboard.type("One.");
  await expect(page.locator("#typing-canvas")).toContainText("Two.");
  await expect(page.getByText("Sentence 2 of 2", { exact: true })).toBeVisible();
  await expect(page.locator("#results-modal")).not.toBeVisible();
  await expect(page.locator("#typing-hidden-input")).toBeFocused();
  await page.keyboard.type("Two.");
  await expect(page.locator("#results-modal")).toBeVisible();
});
