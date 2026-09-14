export type Sentence = {
  index: number;
  text: string;
  translation: string;
  translation_hints: Record<string, string>;
};

export type Paragraph = {
  index: number;
  sentences: Sentence[];
};

export type PracticeSentence = {
  index: number;
  sentence: string;
  translation: string;
  translation_hints: Record<string, string>;
};

export type TextData = {
  title: string;
  original_paragraphs: Paragraph[];
  practice_sentences: PracticeSentence[];
};

export type TextTitle = {
  id: string;
  title: string;
};

export type TextsResponse = {
  message: string;
  data: TextData[];
};

export type TitlesResponse = {
  message: string;
  titles: TextTitle[];
};

export type TextResponse = {
  message: string;
  data: TextData;
};

export type UploadResponse = {
  message: string;
  text: string;
};
