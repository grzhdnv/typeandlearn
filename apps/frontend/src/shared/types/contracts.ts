/**
 * Sentence item in original text paragraphs.
 */
export type Sentence = {
  index: number;
  text: string;
  translation: string;
  translation_hints: Record<string, string>;
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
  translation_hints: Record<string, string>;
};

/**
 * Canonical text payload returned by the backend.
 */
export type TextData = {
  id?: number;
  title: string;
  original_paragraphs: Paragraph[];
  practice_sentences: PracticeSentence[];
};

/**
 * Lightweight title record used in text selection lists.
 */
export type TextTitle = {
  id: string;
  title: string;
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
