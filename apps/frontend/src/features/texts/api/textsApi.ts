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
  // Defensive read compatibility with older APIs/records that serialized nulls.
  const optionalMetadata = (value?: string | null) => {
    const trimmed = value?.trim();
    return trimmed && !/^(null|none|undefined)$/i.test(trimmed) ? trimmed : undefined;
  };
  return (json.titles ?? []).map(text => ({
    ...text,
    author: optionalMetadata(text.author),
    category: optionalMetadata(text.category),
  }));
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
export const postText = async (text: string, language?: string, title?: string, difficultyLevel?: string, author?: string, category?: string, filteringMethod: "spacy" | "llm" = "spacy"): Promise<UploadResponse> => {
  const trimmed = text.trim();
  if (!trimmed) {
    throw new Error("Text cannot be empty");
  }
  return postJson<UploadResponse>("/api/texts", { 
    text: trimmed,
    language: language?.trim() || undefined,
    title: title?.trim() || undefined,
    difficulty_level: difficultyLevel?.trim() || undefined,
    author: author?.trim() || undefined,
    category: category?.trim() || undefined,
    filtering_method: filteringMethod,
  });
};

export const updateProgress = async (id: string, sentenceIndex: number): Promise<{completed_sentences: number}> => {
  return postJson<{completed_sentences: number}>(`/api/texts/${id}/progress`, { sentence_index: sentenceIndex });
};

export const resetProgress = async (id: string): Promise<{completed_sentences: number}> => {
  return postJson<{completed_sentences: number}>(`/api/texts/${id}/reset`, {});
};

export const regenerateTopWords = async (id: string, filteringMethod: "spacy" | "llm" = "spacy"): Promise<TextData> => {
  const response = await postJson<{ message: string; data: TextData }>(`/api/texts/${id}/regenerate-words`, {
    filtering_method: filteringMethod
  });
  return response.data;
};

export const updateTextMetadata = async (id: string, language?: string, difficultyLevel?: string, author?: string, category?: string, title?: string): Promise<TextResponse> => {
  const payload: Record<string, string> = {};
  if (title !== undefined) payload.title = title;
  if (language) payload.language = language;
  if (difficultyLevel) payload.difficulty_level = difficultyLevel;
  if (author !== undefined) payload.author = author;
  if (category !== undefined) payload.category = category;
  
  return patchJson<TextResponse>(`/api/texts/${id}`, payload);
};

export const deleteText = async (id: string): Promise<void> => {
  await deleteJson(`/api/texts/${id}`);
};

export const retryEnrichment = async (id: string): Promise<TextData> => {
  const response = await postJson<{ message: string; data: TextData }>(`/api/texts/${id}/retry`, {});
  return response.data;
};
