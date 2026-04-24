import { createSignal } from "solid-js";

// --- Types ---
type Dictionary = { [key: string]: unknown };

type TextsResponse = {
  message?: string;
  data?: Dictionary[]; // Example shape: [{}, {}]
};

// --- State ---
// "Getters" and "setters" for the state
const [texts, setTexts] = createSignal<Dictionary[]>([]);
const [errorMessage, setErrorMessage] = createSignal("");

// Function to fetch texts, used on button click
const fetchTexts = async () => {
  // Clear old error before starting a new request.
  setErrorMessage("");

  try {
    // Request data through Vite dev proxy (`/api` -> backend server).
    const response = await fetch("/api/texts");

    // If server returned a non-2xx status, treat it as an error.
    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`);
    }

    // Read response content type header, empty string fallback to avoid null/undefined issues.
    const contentType = response.headers.get("content-type") ?? "";

    // Guard: this endpoint should return JSON, not HTML/text.
    if (!contentType.includes("application/json")) {
      throw new Error("Expected JSON response from API");
    }

    // Parse JSON into our `TextsResponse` shape.
    const data: TextsResponse = await response.json();

    // Save returned list to signal. If `data.data` is missing, use empty array to keep UI stable.
    setTexts(data.data ?? []);
  } catch (error) {
    // Any network/parsing/explicit thrown error ends up here.
    // If it is a real Error object, use its message. Otherwise show a fallback message.
    setErrorMessage(error instanceof Error ? error.message : "Unknown error");
  }
};

export type StoryData = {
  title: string;
  original_paragraphs: {
    sentences: {
      text: string;
      translation: string;
      translation_hints: Record<string, string>;
    }[];
  }[];
  practice_sentences: {
    sentence: string;
    translation: string;
    translation_hints: Record<string, string>;
  }[];
};

export type TextTitle = {
  id: string;
  title: string;
};

type TextTitlesResponse = {
  message?: string;
  titles?: TextTitle[];
};

export const fetchTextTitles = async (): Promise<TextTitle[]> => {
  const response = await fetch("/api/texts/titles");
  if (!response.ok)
    throw new Error(`Request failed with status ${response.status}`);
  const json: TextTitlesResponse = await response.json();
  return json.titles ?? [];
};

export const fetchStory = async (id: string = "00"): Promise<StoryData> => {
  const response = await fetch(`/api/texts/${id}`);
  if (!response.ok)
    throw new Error(`Request failed with status ${response.status}`);
  const json = await response.json();
  return json.data as StoryData;
};
