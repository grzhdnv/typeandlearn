/**
 * Sentence item in original text paragraphs.
 */
export type HintGroup = {
  words: string[];
  hint: string;
};

/**
 * Sentence item in original text paragraphs.
 */
export type Sentence = {
  index: number;
  text: string;
  translation: string;
  translation_hints: HintGroup[];
};

/**
 * Paragraph grouping of source sentences.
 */
export type Paragraph = {
  index: number;
  sentences: Sentence[];
};

/**
 * Generated practice sentence with translation metadata.
 */
export type PracticeSentence = {
  index: number;
  sentence: string;
  translation: string;
  translation_hints: HintGroup[];
};

/**
 * Top frequency word with optional translation.
 */
export type TopWord = {
  word: string;
  translation?: string;
};

/**
 * Canonical text payload returned by the backend.
 */
export type TextData = {
  id?: number;
  title: string;
  status: string;
  language: string;
  difficulty_level: string;
  author?: string;
  category?: string;
  word_count: number;
  completed_sentences: number;
  total_sentences: number;
  estimated_time_minutes: number;
  original_paragraphs: Paragraph[];
  practice_sentences: PracticeSentence[];
  top_words: TopWord[];
  enrichment_stage?: string;
  error_message?: string;
};

/**
 * Lightweight title record used in text selection lists.
 */
export type TextTitle = {
  id: string;
  title: string;
  status: string;
  language: string;
  difficulty_level: string;
  author?: string;
  category?: string;
  word_count: number;
  completed_sentences: number;
  total_sentences: number;
  estimated_time_minutes: number;
  enrichment_stage?: string;
  error_message?: string;
};

/**
 * API response for all stored text entries.
 */
export type TextsResponse = {
  message: string;
  data: TextData[];
};

/**
 * API response containing text titles only.
 */
export type TitlesResponse = {
  message: string;
  titles: TextTitle[];
};

/**
 * API response containing a single text entry.
 */
export type TextResponse = {
  message: string;
  data: TextData;
};

/**
 * API response returned after successful text submission.
 */
export type UploadResponse = {
  message: string;
  text: string;
};

/**
 * Persisted typing practice session drill record.
 */
export type PracticeSession = {
  id: number;
  owner_id: string;
  text_id: number;
  sentence_index: number;
  sentence_text: string;
  target_type: string;
  net_wpm: number;
  raw_wpm: number;
  accuracy: number;
  active_seconds: number;
  mistake_count: number;
  mistakes_detail?: Array<Record<string, unknown>>;
  completed_at: string;
};

/**
 * Creation payload sent upon completing a typing drill.
 */
export type PracticeSessionCreatePayload = {
  text_id: number;
  sentence_index: number;
  sentence_text: string;
  target_type?: string;
  net_wpm: number;
  raw_wpm: number;
  accuracy: number;
  active_seconds: number;
  mistake_count: number;
  mistakes_detail?: Array<Record<string, unknown>>;
  mistaken_words?: string[];
};

/**
 * Frequently missed vocabulary item with mistake counts.
 */
export type WeakWord = {
  id: number;
  owner_id: string;
  language: string;
  word: string;
  mistake_count: number;
  practice_count: number;
  last_mistake_at: string;
};

/**
 * Progression data point tracking WPM and accuracy over time.
 */
export type SessionTrendPoint = {
  session_id: number;
  completed_at: string;
  net_wpm: number;
  accuracy: number;
};

/**
 * Aggregate lifetime KPIs and recent progression metrics.
 */
export type AnalyticsSummary = {
  total_drills: number;
  total_practice_seconds: number;
  avg_net_wpm: number;
  peak_net_wpm: number;
  avg_accuracy: number;
  total_mistakes: number;
  recent_trend: SessionTrendPoint[];
};

/**
 * Current user profile and identity introspection.
 */
export type UserProfile = {
  owner_id: string;
  auth_mode: string;
  authenticated: boolean;
};
