import { getJson, patchJson, postJson, deleteJson } from "../../../shared/api/http";
import type {
  TextData,
  TextResponse,
  TextTitle,
  TitlesResponse,
  UploadResponse,
} from "../../../shared/types/contracts";

/**
 * Fetches lightweight text metadata for the selector dropdown.
 */
export const fetchTextTitles = async (): Promise<TextTitle[]> => {
  const json = await getJson<TitlesResponse>("/api/texts/titles");
  return json.titles ?? [];
};

/**
 * Fetches a full story payload by backend text id.
 *
 * @param id Text id returned by the titles endpoint.
 */
export const fetchStory = async (id: string): Promise<TextData> => {
  const json = await getJson<TextResponse>(`/api/texts/${id}`);
  return json.data;
};

/**
 * Submits raw text for backend processing and persistence.
 *
 * @param text Raw user input from the editor.
 */
export const postText = async (text: string, language: string, title?: string, difficultyLevel?: string): Promise<UploadResponse> => {
  const trimmed = text.trim();
  if (!trimmed) {
    throw new Error("Text cannot be empty");
  }
  return postJson<UploadResponse>("/api/texts", { 
    text: trimmed,
    language,
    title: title?.trim() || undefined,
    difficulty_level: difficultyLevel?.trim() || undefined
  });
};

export const updateProgress = async (id: string, sentenceIndex: number): Promise<{completed_sentences: number}> => {
  return postJson<{completed_sentences: number}>(`/api/texts/${id}/progress`, { sentence_index: sentenceIndex });
};

export const resetProgress = async (id: string): Promise<{completed_sentences: number}> => {
  return postJson<{completed_sentences: number}>(`/api/texts/${id}/reset`, {});
};

export const updateTextMetadata = async (id: string, language?: string, difficultyLevel?: string): Promise<TextResponse> => {
  const payload: Record<string, string> = {};
  if (language) payload.language = language;
  if (difficultyLevel) payload.difficulty_level = difficultyLevel;
  
  return patchJson<TextResponse>(`/api/texts/${id}`, payload);
};

export const deleteText = async (id: string): Promise<void> => {
  await deleteJson(`/api/texts/${id}`);
};
