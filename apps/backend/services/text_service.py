"""Domain service for text retrieval, upload, and deletion workflows."""

from itertools import groupby

from models.texts import PracticeSentenceRecord, SentenceRecord, TextRecord, WordFrequencyRecord
from repositories.text_repository import TextRepository
from schemas.texts import Paragraph, PracticeSentence, Sentence, TextData, TextTitle
from services.llm_service import LlmService
from services.preprocessing_service import PreprocessingService


class TextService:
    """Coordinate repository persistence with NLP-backed preprocessing and generation."""

    def __init__(self, repository: TextRepository, llm: LlmService, preprocessing: PreprocessingService) -> None:
        """Bind storage and generation dependencies."""
        self._repository = repository
        self._llm = llm
        self._preprocessing = preprocessing

    def _build_text_data(
        self,
        record: TextRecord,
        sentence_records: list[SentenceRecord],
        practice_records: list[PracticeSentenceRecord],
    ) -> TextData:
        """Reconstruct the nested API response from flat database records."""

        paragraphs = []
        # Group sentences by paragraph_index
        for p_idx, s_group in groupby(
            sentence_records, key=lambda s: s.paragraph_index
        ):
            sentences = []
            for s in s_group:
                hints = s.translation_hints or []
                if isinstance(hints, dict):
                    hints = [{"words": [k], "hint": v} for k, v in hints.items()]

                sentences.append(
                    Sentence(
                        index=s.sentence_index,
                        text=s.original_text,
                        translation=s.translation or "",
                        translation_hints=hints,
                    )
                )
            paragraphs.append(Paragraph(index=p_idx, sentences=sentences))

        practice_sentences = []
        for p in practice_records:
            hints = p.translation_hints or []
            if isinstance(hints, dict):
                hints = [{"words": [k], "hint": v} for k, v in hints.items()]
                
            practice_sentences.append(
                PracticeSentence(
                    index=p.sentence_index,
                    sentence=p.sentence,
                    translation=p.translation,
                    translation_hints=hints,
                )
            )

        return TextData(
            id=record.id,
            title=record.title,
            status=record.status,
            original_paragraphs=paragraphs,
            practice_sentences=practice_sentences,
        )

    def get_all(self) -> list[TextData]:
        """Return all stored text entries."""
        records = self._repository.load_all_texts()
        results = []
        for record in records:
            if record.id is None:
                continue
            s_records = self._repository.load_sentences(record.id)
            p_records = self._repository.load_practice_sentences(record.id)
            results.append(self._build_text_data(record, s_records, p_records))
        return results

    def get_titles(self) -> list[TextTitle]:
        """Return database-backed title metadata for text selection."""
        titles = self._repository.load_titles()
        return [TextTitle(id=str(tid), title=title) for tid, title in titles]

    def get_one(self, text_id: str) -> TextData:
        """Return one text entry by its database ID."""
        try:
            tid = int(text_id)
        except ValueError as error:
            raise ValueError(f"Invalid text ID format: {text_id}") from error

        record = self._repository.load_one_text(tid)
        if record is None or record.id is None:
            raise IndexError("Text not found")

        s_records = self._repository.load_sentences(record.id)
        p_records = self._repository.load_practice_sentences(record.id)

        return self._build_text_data(record, s_records, p_records)

    def upload(self, text: str, title: str = "New Uploaded Text") -> TextRecord:
        """Generate and persist a new text entry from raw input using local preprocessing."""
        
        # 1. Preprocess the text locally using spaCy
        paragraphs_data, word_frequencies = self._preprocessing.process_text(text)
        
        # 2. Save the TextRecord (marked as processing initially since LLM work isn't done yet)
        record = TextRecord(title=title, status="processing")
        record = self._repository.save_text(record)
        
        if record.id is None:
            raise RuntimeError("Failed to generate database ID for text.")
            
        # 3. Save the blank sentences (translations will be generated later)
        sentence_records = []
        for p in paragraphs_data:
            for s in p["sentences"]:
                sentence_records.append(
                    SentenceRecord(
                        text_id=record.id,
                        paragraph_index=p["index"],
                        sentence_index=s["index"],
                        original_text=s["text"],
                        translation="",
                        translation_hints=[],
                        status="pending"
                    )
                )
        self._repository.save_sentences(sentence_records)
        
        # 4. Save the word frequencies for later use in generating practice sentences
        frequency_records = []
        for wf in word_frequencies:
            frequency_records.append(
                WordFrequencyRecord(
                    text_id=record.id,
                    word=wf["word"],
                    count=wf["count"]
                )
            )
        self._repository.save_word_frequencies(frequency_records)

        return record

    def delete(self, text_id: str) -> TextData:
        """Delete and return one text entry by its database ID."""
        try:
            tid = int(text_id)
        except ValueError as error:
            raise ValueError(f"Invalid text ID format: {text_id}") from error

        # Load it first so we can return the deleted data to the frontend
        record = self._repository.load_one_text(tid)
        if record is None or record.id is None:
            raise IndexError("Text not found")

        s_records = self._repository.load_sentences(record.id)
        p_records = self._repository.load_practice_sentences(record.id)
        data_to_return = self._build_text_data(record, s_records, p_records)

        self._repository.delete_text(tid)
        return data_to_return

    def process_pending_text(self, text_id: int) -> None:
        """Background worker to translate sentences and generate practice sentences."""
        record = self._repository.load_one_text(text_id)
        if not record or record.status != "processing":
            return
            
        s_records = self._repository.load_sentences(text_id)
        
        # Helper to get full paragraph for context
        def get_paragraph_context(p_idx: int) -> str:
            return " ".join([s.original_text for s in s_records if s.paragraph_index == p_idx])

        # 1. Translate sentences
        total_sentences = len(s_records)
        processed_count = sum(1 for s in s_records if s.status == "processed")
        
        print(f"Starting background processing for text '{record.title}' (ID: {text_id}). {processed_count}/{total_sentences} sentences already processed.")
        
        for idx, s in enumerate(s_records, start=1):
            if s.status != "pending":
                continue
                
            print(f"[{idx}/{total_sentences}] Translating sentence: '{s.original_text}'...")
            context = get_paragraph_context(s.paragraph_index)
            try:
                result = self._llm.translate_sentence(
                    title=record.title,
                    context=context,
                    target_sentence=s.original_text
                )
                
                s.translation = result.translation
                # Convert Pydantic HintGroup models to dicts for JSON storage
                s.translation_hints = [hg.model_dump() for hg in result.translation_hints]
                s.status = "processed"
                self._repository.update_sentence(s)
                print(f"  -> Translated: '{s.translation}'")
            except Exception as e:
                # Log error and potentially retry later, but for now we continue
                print(f"  [ERROR] Failed to translate sentence {s.id}: {e}")

        # 2. Generate Practice Sentences
        frequencies = self._repository.load_word_frequencies(text_id)
        # Take the top 15 words to seed the practice sentence generator
        top_words = [f.word for f in frequencies[:15]]
        
        if top_words:
            print(f"Generating practice sentences using top {len(top_words)} words: {top_words}")
            try:
                practice_result = self._llm.generate_practice_sentences(top_words)
                
                practice_records = []
                for idx, ps in enumerate(practice_result.sentences):
                    practice_records.append(
                        PracticeSentenceRecord(
                            text_id=text_id,
                            sentence_index=idx,
                            sentence=ps.sentence,
                            translation=ps.translation,
                            translation_hints=[hg.model_dump() for hg in ps.translation_hints]
                        )
                    )
                self._repository.save_practice_sentences(practice_records)
            except Exception as e:
                print(f"Failed to generate practice sentences for text {text_id}: {e}")
                
        # 3. Mark text as fully processed
        record.status = "processed"
        self._repository.update_text(record)
        print(f"Successfully finished processing text '{record.title}' (ID: {text_id})!")
