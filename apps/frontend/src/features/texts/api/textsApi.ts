import { getJson, postJson } from "../../../shared/api/http";
import type {
  TextData,
  TextResponse,
  TextTitle,
  TitlesResponse,
  UploadResponse,
} from "../../../shared/types/contracts";

export const fetchTextTitles = async (): Promise<TextTitle[]> => {
  const json = await getJson<TitlesResponse>("/api/texts/titles");
  return json.titles ?? [];
};

export const fetchStory = async (id: string): Promise<TextData> => {
  const json = await getJson<TextResponse>(`/api/texts/${id}`);
  return json.data;
};

export const postText = async (text: string): Promise<UploadResponse> => {
  const trimmed = text.trim();
  if (!trimmed) {
    throw new Error("Text cannot be empty");
  }
  return postJson<UploadResponse>("/api/texts", { text: trimmed });
};
