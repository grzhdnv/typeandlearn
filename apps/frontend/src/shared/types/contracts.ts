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
