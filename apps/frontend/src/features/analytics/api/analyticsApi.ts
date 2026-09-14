import { getJson, postJson } from "../../../shared/api/http";
import type {
  AnalyticsSummary,
  PracticeSession,
  PracticeSessionCreatePayload,
  WeakWord,
} from "../../../shared/types/contracts";

export const recordPracticeSession = async (
  payload: PracticeSessionCreatePayload
): Promise<PracticeSession> => {
  return postJson<PracticeSession>("/api/analytics/sessions", payload);
};

export const fetchSessionHistory = async (
  limit = 50,
  offset = 0
): Promise<PracticeSession[]> => {
  return getJson<PracticeSession[]>(`/api/analytics/history?limit=${limit}&offset=${offset}`);
};

export const fetchAnalyticsSummary = async (): Promise<AnalyticsSummary> => {
  return getJson<AnalyticsSummary>("/api/analytics/summary");
};

export const fetchWeakWords = async (
  language?: string,
  limit = 20
): Promise<WeakWord[]> => {
  const url = language
    ? `/api/analytics/weak-words?language=${encodeURIComponent(language)}&limit=${limit}`
    : `/api/analytics/weak-words?limit=${limit}`;
  return getJson<WeakWord[]>(url);
};
