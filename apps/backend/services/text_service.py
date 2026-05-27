"""Domain service for text retrieval, upload, and deletion workflows."""

from itertools import groupby

from models.texts import PracticeSentenceRecord, SentenceRecord, TextRecord
from repositories.text_repository import TextRepository
from schemas.texts import Paragraph, PracticeSentence, Sentence, TextData, TextTitle
from services.llm_service import LlmService


class TextService:
    """Coordinate repository persistence with LLM-backed processing."""

    def __init__(self, repository: TextRepository, llm: LlmService) -> None:
        """Bind storage and generation dependencies."""
        self._repository = repository
        self._llm = llm

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
                sentences.append(
                    Sentence(
                        index=s.sentence_index,
                        text=s.original_text,
                        translation=s.translation or "",
                        translation_hints=s.translation_hints or {},
                    )
                )
            paragraphs.append(Paragraph(index=p_idx, sentences=sentences))

        practice_sentences = [
            PracticeSentence(
                index=p.sentence_index,
                sentence=p.sentence,
                translation=p.translation,
                translation_hints=p.translation_hints or {},
            )
            for p in practice_records
        ]

        return TextData(
            id=record.id,
            title=record.title,
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

    def upload(self, text: str) -> TextRecord:
        """Generate and persist a new text entry from raw input."""

        # We continue using the old LLM generation for now, but we flatten it for the new DB.
        new_entry = self._llm.text_to_db(text)

        record = TextRecord(title=new_entry.title, status="completed")
        record = self._repository.save_text(record)

        if record.id is None:
            raise RuntimeError("Failed to generate database ID for text.")

        sentence_records = []
        for paragraph in new_entry.original_paragraphs:
            for s in paragraph.sentences:
                sentence_records.append(
                    SentenceRecord(
                        text_id=record.id,
                        paragraph_index=paragraph.index,
                        sentence_index=s.index,
                        original_text=s.text,
                        translation=s.translation,
                        translation_hints=s.translation_hints,
                        status="completed",
                    )
                )
        self._repository.save_sentences(sentence_records)

        practice_records = []
        for p in new_entry.practice_sentences:
            practice_records.append(
                PracticeSentenceRecord(
                    text_id=record.id,
                    sentence_index=p.index,
                    sentence=p.sentence,
                    translation=p.translation,
                    translation_hints=p.translation_hints,
                )
            )
        self._repository.save_practice_sentences(practice_records)

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
