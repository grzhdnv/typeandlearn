import { getJson, postJson } from "../../../shared/api/http";
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
export const postText = async (text: string): Promise<UploadResponse> => {
  const trimmed = text.trim();
  if (!trimmed) {
    throw new Error("Text cannot be empty");
  }
  return postJson<UploadResponse>("/api/texts", { text: trimmed });
};
