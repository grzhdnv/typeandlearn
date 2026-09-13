"""Domain service for text retrieval, upload, and deletion workflows."""

import concurrent.futures
import random
import time
from itertools import groupby
from typing import Optional

from sqlmodel import Session

from models.cache import compute_sentence_hash
from models.texts import PracticeSentenceRecord, SentenceRecord, TextRecord, WordFrequencyRecord
from repositories.cache_repository import CacheRepository, DailyBudgetExceededError
from repositories.job_repository import JobRepository
from repositories.text_repository import TextRepository
from schemas.texts import HintGroup, Paragraph, PracticeSentence, Sentence, TextData, TextTitle, TextUpdateRequest, TopWord
from services.dictionary_service import DictionaryService
from services.llm_service import LlmService
from services.preprocessing_service import PreprocessingService


class TextService:
    """Coordinate repository persistence with NLP-backed preprocessing and generation."""

    def __init__(
        self,
        repository: TextRepository,
        llm: LlmService,
        preprocessing: PreprocessingService,
        dictionary: DictionaryService,
        job_repository: Optional[JobRepository] = None,
        cache_repository: Optional[CacheRepository] = None,
        daily_token_limit: int = 50_000,
        prompt_version: str = "v1",
    ) -> None:
        """Bind storage, generation, caching, and background job dependencies."""
        self._repository = repository
        self._llm = llm
        self._preprocessing = preprocessing
        self._dictionary = dictionary
        self._job_repository = job_repository
        self._cache_repository = cache_repository
        self._daily_token_limit = daily_token_limit
        self._prompt_version = prompt_version

    def _build_text_data(
        self,
        record: TextRecord,
        sentence_records: list[SentenceRecord],
        practice_records: list[PracticeSentenceRecord],
        top_words: list[TopWord] | None = None,
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
                        translation_hints=[HintGroup(**h) for h in hints] if hints else [],
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
                    translation_hints=[HintGroup(**h) for h in hints] if hints else [],
                )
            )

        return TextData(
            id=record.id,
            title=record.title,
            status=record.status,
            language=record.language,
            difficulty_level=record.difficulty_level,
            author=record.author,
            category=record.category,
            word_count=record.word_count,
            completed_sentences=record.completed_sentences,
            total_sentences=record.total_sentences,
            estimated_time_minutes=record.estimated_time_minutes,
            original_paragraphs=paragraphs,
            practice_sentences=practice_sentences,
            top_words=top_words or [],
        )

    def get_all(self, owner_id: str) -> list[TextData]:
        """Return all stored text entries for an owner."""
        records = self._repository.load_all_texts(owner_id)
        results = []
        for record in records:
            if record.id is None:
                continue
            s_records = self._repository.load_sentences(record.id, owner_id)
            p_records = self._repository.load_practice_sentences(record.id, owner_id)
            results.append(self._build_text_data(record, s_records, p_records))
        return results

    def get_titles(self, owner_id: str) -> list[TextTitle]:
        """Return database-backed title metadata for text selection."""
        records = self._repository.load_titles(owner_id)
        return [
            TextTitle(
                id=str(record.id), 
                title=record.title,
                status=record.status,
                language=record.language,
                difficulty_level=record.difficulty_level,
                word_count=record.word_count,
                completed_sentences=record.completed_sentences,
                total_sentences=record.total_sentences,
                estimated_time_minutes=record.estimated_time_minutes
            ) 
            for record in records
        ]

    def get_one(self, text_id: str, owner_id: str) -> TextData:
        """Return one text entry by its database ID and owner ID."""
        try:
            tid = int(text_id)
        except ValueError as error:
            raise ValueError(f"Invalid text ID format: {text_id}") from error

        record = self._repository.load_one_text(tid, owner_id)
        if record is None or record.id is None:
            raise IndexError("Text not found")

        s_records = self._repository.load_sentences(record.id, owner_id)
        p_records = self._repository.load_practice_sentences(record.id, owner_id)
        frequencies = self._repository.load_word_frequencies(record.id, owner_id)
        top_words = [TopWord(word=f.word, translation=f.translation) for f in frequencies[:15]]

        return self._build_text_data(record, s_records, p_records, top_words)

    def upload(
        self,
        text: str,
        language: str,
        owner_id: str,
        title: str | None = None,
        difficulty_level: str | None = None,
        author: str | None = None,
        category: str | None = None,
        filtering_method: str = "spacy",
    ) -> TextRecord:
        """Generate and persist a new text entry from raw input using local preprocessing."""
        
        # 1. Preprocess the text locally using spaCy
        paragraphs_data, word_frequencies = self._preprocessing.process_text(text, language, filtering_method)
        
        if filtering_method == "llm":
            for attempt in range(4):
                try:
                    filtered_response = self._llm.filter_meaningful_words(word_frequencies, language)
                    word_frequencies = [{"word": fw.word, "count": fw.count} for fw in filtered_response.words]
                    break
                except Exception as e:
                    if "429" in str(e).lower() or "rate limit" in str(e).lower():
                        if attempt < 3:
                            time.sleep(2 ** attempt)
                            continue
                    print(f"Failed to filter words via LLM: {e}")
                    # Fallback to spacy logic if LLM fails
                    break
        
        # 2. Extract metadata if missing
        final_title = title
        final_difficulty = difficulty_level
        if not final_title or not final_difficulty:
            for attempt in range(4):
                try:
                    metadata = self._llm.extract_metadata(text)
                    if not final_title:
                        final_title = f"[{metadata.title}]"
                    if not final_difficulty:
                        final_difficulty = metadata.difficulty_level
                    break
                except Exception as e:
                    if "429" in str(e).lower() or "rate limit" in str(e).lower():
                        if attempt < 3:
                            time.sleep(2 ** attempt)
                            continue
                    print(f"Failed to extract metadata: {e}")
                    if not final_title:
                        final_title = "[Untitled]"
                    if not final_difficulty:
                        final_difficulty = "Unrated"
                    break

        final_title = final_title or "[Untitled]"
        final_difficulty = final_difficulty or "Unrated"

        # Calculate basic metrics
        word_count = sum(len(s["text"].split()) for p in paragraphs_data for s in p["sentences"])
        total_sentences = sum(len(p["sentences"]) for p in paragraphs_data)
        estimated_time = max(1, word_count // 40)
        
        # 3. Save the TextRecord
        record = TextRecord(
            owner_id=owner_id,
            title=final_title, 
            status="processing",
            language=language,
            difficulty_level=final_difficulty,
            author=author,
            category=category,
            word_count=word_count,
            total_sentences=total_sentences,
            estimated_time_minutes=estimated_time
        )
        # 3. Save the blank sentences (translations will be generated later)
        sentence_records = []
        for p in paragraphs_data:
            for s in p["sentences"]:
                sentence_records.append(
                    SentenceRecord(
                        text_id=0,
                        owner_id=owner_id,
                        paragraph_index=p["index"],
                        sentence_index=s["index"],
                        original_text=s["text"],
                        translation="",
                        translation_hints=[],
                        status="pending",
                    )
                )

        # 4. Save the word frequencies for later use in generating practice sentences
        frequency_records = []
        for wf in word_frequencies:
            frequency_records.append(
                WordFrequencyRecord(
                    text_id=0,
                    owner_id=owner_id,
                    word=wf["word"],
                    count=wf["count"],
                )
            )

        job_payload = {
            "owner_id": owner_id,
            "filtering_method": filtering_method,
            "language": language,
        }

        if hasattr(self._repository, "save_text_with_job"):
            record, _ = self._repository.save_text_with_job(
                record=record,
                task_type="process_text",
                payload=job_payload,
                sentences=sentence_records,
                frequencies=frequency_records,
            )
        else:
            record = self._repository.save_text(record)
            if record.id is None:
                raise RuntimeError("Failed to generate database ID for text.")
            for s in sentence_records:
                s.text_id = record.id
            self._repository.save_sentences(sentence_records)
            for f in frequency_records:
                f.text_id = record.id
            self._repository.save_word_frequencies(frequency_records)

        return record

    def delete(self, text_id: str, owner_id: str) -> TextData:
        """Delete and return one text entry by its database ID and owner ID."""
        try:
            tid = int(text_id)
        except ValueError as error:
            raise ValueError(f"Invalid text ID format: {text_id}") from error

        # Load it first so we can return the deleted data to the frontend
        record = self._repository.load_one_text(tid, owner_id)
        if record is None or record.id is None:
            raise IndexError("Text not found")

        s_records = self._repository.load_sentences(record.id, owner_id)
        p_records = self._repository.load_practice_sentences(record.id, owner_id)
        data_to_return = self._build_text_data(record, s_records, p_records)

        self._repository.delete_text(tid, owner_id)
        return data_to_return

    def regenerate_words(self, text_id: str, owner_id: str, filtering_method: str = "spacy") -> TextData:
        """Regenerate word frequencies and trigger practice sentence regeneration."""
        try:
            tid = int(text_id)
        except ValueError as error:
            raise ValueError(f"Invalid text ID format: {text_id}") from error

        record = self._repository.load_one_text(tid, owner_id)
        if record is None or record.id is None:
            raise IndexError("Text not found")
            
        s_records = self._repository.load_sentences(record.id, owner_id)
        full_text = " ".join(s.original_text for s in s_records)
        
        # 1. Re-extract word frequencies using new logic
        _, word_frequencies = self._preprocessing.process_text(full_text, record.language, filtering_method)
        
        if filtering_method == "llm":
            for attempt in range(4):
                try:
                    filtered_response = self._llm.filter_meaningful_words(word_frequencies, record.language)
                    word_frequencies = [{"word": fw.word, "count": fw.count} for fw in filtered_response.words]
                    break
                except Exception as e:
                    if "429" in str(e).lower() or "rate limit" in str(e).lower():
                        if attempt < 3:
                            time.sleep(2 ** attempt)
                            continue
                    print(f"Failed to filter words via LLM during regeneration: {e}")
                    raise ValueError(f"LLM filtering failed: {e}")
        
        # 2. Update WordFrequencyRecords
        self._repository.delete_word_frequencies(record.id, owner_id)
        frequency_records = []
        for wf in word_frequencies:
            frequency_records.append(
                WordFrequencyRecord(
                    owner_id=owner_id,
                    text_id=record.id,
                    word=wf["word"],
                    count=wf["count"]
                )
            )
        self._repository.save_word_frequencies(frequency_records)
        
        # 3. Set status to processing to trigger background generation
        record.status = "processing"
        self._repository.update_text(record)

        if self._job_repository and record.id is not None:
            with Session(self._repository._engine) as session:
                self._job_repository.enqueue(
                    session=session,
                    owner_id=owner_id,
                    task_type="process_text",
                    payload={"text_id": record.id, "owner_id": owner_id, "filtering_method": filtering_method},
                    text_id=record.id,
                )
                session.commit()
        
        return self.get_one(text_id, owner_id)

    def update_progress(self, text_id: str, sentence_index: int, owner_id: str) -> TextRecord:
        """Update the completed sentences count for a text by tracking unique completed indices."""
        try:
            tid = int(text_id)
        except ValueError as error:
            raise ValueError(f"Invalid text ID format: {text_id}") from error

        record = self._repository.load_one_text(tid, owner_id)
        if record is None or record.id is None:
            raise IndexError("Text not found")
            
        indices = set(record.completed_sentence_indices or [])
        if sentence_index not in indices:
            indices.add(sentence_index)
            record.completed_sentence_indices = list(indices)
            record.completed_sentences = len(indices)
            return self._repository.update_text(record)
            
        return record

    def reset_progress(self, text_id: str, owner_id: str) -> TextRecord:
        """Reset the completed sentences count for a text."""
        try:
            tid = int(text_id)
        except ValueError as error:
            raise ValueError(f"Invalid text ID format: {text_id}") from error

        record = self._repository.load_one_text(tid, owner_id)
        if record is None or record.id is None:
            raise IndexError("Text not found")
            
        record.completed_sentences = 0
        record.completed_sentence_indices = []
        return self._repository.update_text(record)

    def update_metadata(self, text_id: str, payload: TextUpdateRequest, owner_id: str) -> TextData:
        """Update language and/or difficulty level of a text."""
        try:
            tid = int(text_id)
        except ValueError as error:
            raise ValueError(f"Invalid text ID format: {text_id}") from error

        record = self._repository.load_one_text(tid, owner_id)
        if record is None or record.id is None:
            raise IndexError("Text not found")
            
        if payload.language is not None:
            record.language = payload.language
        if payload.difficulty_level is not None:
            record.difficulty_level = payload.difficulty_level
        if payload.author is not None:
            record.author = payload.author
        if payload.category is not None:
            record.category = payload.category
            
        self._repository.update_text(record)
        return self.get_one(text_id, owner_id)

    def process_pending_text(self, text_id: int, owner_id: str) -> None:
        """Background worker to translate sentences and generate practice sentences."""
        record = self._repository.load_one_text(text_id, owner_id)
        if not record or record.status != "processing":
            return
            
        s_records = self._repository.load_sentences(text_id, owner_id)
        
        # Helper to get just the previous sentence for context (drastically reduces tokens)
        def get_previous_sentence_context(current_s) -> str:
            sorted_records = sorted(s_records, key=lambda x: (x.paragraph_index, x.sentence_index))
            try:
                curr_idx = sorted_records.index(current_s)
                if curr_idx > 0:
                    return sorted_records[curr_idx - 1].original_text
                return ""
            except ValueError:
                return ""

        # 1. Translate sentences
        total_sentences = len(s_records)
        processed_count = sum(1 for s in s_records if s.status == "processed")
        
        print(f"Starting background processing for text '{record.title}' (ID: {text_id}). {processed_count}/{total_sentences} sentences already processed.")
        
        import asyncio
        
        async def _translate_all():
            sem = asyncio.Semaphore(15)
            
            async def _translate_and_update(s, idx):
                if s.status != "pending":
                    return

                sentence_hash = compute_sentence_hash(s.original_text)

                # Check translation cache before invoking LLM
                if self._cache_repository:
                    cached = await asyncio.to_thread(
                        self._cache_repository.get_translation,
                        source_language=record.language,
                        target_language="English",
                        sentence_hash=sentence_hash,
                        prompt_version=self._prompt_version,
                    )
                    if cached:
                        s.translation = cached.translation
                        hints = cached.translation_hints
                        if isinstance(hints, dict) and "hints" in hints:
                            s.translation_hints = hints["hints"]
                        elif isinstance(hints, list):
                            s.translation_hints = hints
                        else:
                            s.translation_hints = []
                        s.status = "processed"
                        await asyncio.to_thread(self._repository.update_sentence, s)
                        print(f"  -> Cache hit for sentence {idx}: '{s.translation}'")
                        return

                # Check daily budget before invoking LLM on cache miss
                if self._cache_repository:
                    has_budget = await asyncio.to_thread(
                        self._cache_repository.check_daily_budget,
                        owner_id=owner_id,
                        daily_limit=self._daily_token_limit,
                    )
                    if not has_budget:
                        print(f"  [ERROR] Daily token budget of {self._daily_token_limit} exceeded for owner {owner_id}")
                        raise DailyBudgetExceededError(
                            f"Daily token budget of {self._daily_token_limit} exceeded for owner {owner_id}"
                        )
                    
                print(f"[{idx}/{total_sentences}] Translating sentence: '{s.original_text}'...")
                context = get_previous_sentence_context(s)
                
                max_retries = 5
                base_delay = 2
                
                async with sem:
                    for attempt in range(max_retries):
                        try:
                            result = await self._llm.translate_sentence_async(
                                title=record.title,
                                context=context,
                                target_sentence=s.original_text,
                            )
                            usage = getattr(result, "usage", None)
                            
                            s.translation = result.translation
                            s.translation_hints = [hg.model_dump() for hg in result.translation_hints]
                            s.status = "processed"
                            await asyncio.to_thread(self._repository.update_sentence, s)
                            print(f"  -> Translated: '{s.translation}'")

                            # Store translation in cache
                            if self._cache_repository:
                                await asyncio.to_thread(
                                    self._cache_repository.store_translation,
                                    source_language=record.language,
                                    target_language="English",
                                    sentence_hash=sentence_hash,
                                    translation=result.translation,
                                    translation_hints=s.translation_hints,
                                    prompt_version=self._prompt_version,
                                )

                            # Record token usage
                            if self._cache_repository and usage is not None:
                                prompt_tokens = getattr(usage, "input_tokens", None)
                                if prompt_tokens is None:
                                    prompt_tokens = getattr(usage, "request_tokens", 0) or 0
                                completion_tokens = getattr(usage, "output_tokens", None)
                                if completion_tokens is None:
                                    completion_tokens = getattr(usage, "response_tokens", 0) or 0
                                total_tokens = getattr(usage, "total_tokens", 0) or (prompt_tokens + completion_tokens)

                                if total_tokens > 0:
                                    spec = getattr(self._llm, "model_name", getattr(self._llm, "_model_name", "unknown"))
                                    provider, model = spec.split(":", 1) if ":" in spec else ("unknown", spec)
                                    est_cost = (prompt_tokens * 0.59 + completion_tokens * 0.79) / 1_000_000.0
                                    await asyncio.to_thread(
                                        self._cache_repository.record_usage,
                                        owner_id=owner_id,
                                        provider=provider,
                                        model=model,
                                        prompt_tokens=prompt_tokens,
                                        completion_tokens=completion_tokens,
                                        total_tokens=total_tokens,
                                        estimated_cost_usd=est_cost,
                                    )
                            return # Success
                        except DailyBudgetExceededError:
                            raise
                        except Exception as e:
                            error_msg = str(e).lower()
                            if "429" in error_msg or "too many requests" in error_msg or "rate limit" in error_msg:
                                delay = (base_delay ** attempt) + random.uniform(0, 1)
                                print(f"  [WARN] Rate limit hit on sentence {s.id}. Retrying in {delay:.2f}s (Attempt {attempt + 1}/{max_retries})")
                                await asyncio.sleep(delay)
                            elif "validation" in error_msg or "unexpectedmodelbehavior" in error_msg:
                                print(f"  [WARN] LLM validation error on sentence {s.id}. Retrying... (Attempt {attempt + 1}/{max_retries})")
                                await asyncio.sleep(1)
                            else:
                                print(f"  [ERROR] Failed to translate sentence {s.id}: {e}")
                                break
                                
            await asyncio.gather(*[_translate_and_update(s, idx) for idx, s in enumerate(s_records, start=1)])

        asyncio.run(_translate_all())

        # 2. Generate Practice Sentences
        frequencies = self._repository.load_word_frequencies(text_id, owner_id)
        # Take the top 15 words to seed the practice sentence generator
        top_words = [f.word for f in frequencies[:15]]
        
        if top_words:
            if self._cache_repository and not self._cache_repository.check_daily_budget(owner_id, self._daily_token_limit):
                raise DailyBudgetExceededError(
                    f"Daily token budget of {self._daily_token_limit} exceeded for owner {owner_id}"
                )

            print(f"Generating practice sentences using top {len(top_words)} words: {top_words}")
            for attempt in range(3):
                try:
                    import asyncio
                    practice_result = asyncio.run(self._llm.generate_practice_sentences_async(top_words))
                    practice_usage = getattr(practice_result, "usage", None)
                    
                    # Clear old practice sentences if any exist (e.g. during regeneration)
                    self._repository.delete_practice_sentences(text_id, owner_id)
                    
                    practice_records = []
                    for idx, ps in enumerate(practice_result.sentences):
                        practice_records.append(
                            PracticeSentenceRecord(
                                owner_id=owner_id,
                                text_id=text_id,
                                sentence_index=idx,
                                sentence=ps.sentence,
                                translation=ps.translation,
                                translation_hints=[hg.model_dump() for hg in ps.translation_hints]
                            )
                        )
                    self._repository.save_practice_sentences(practice_records)

                    if self._cache_repository and practice_usage is not None:
                        p_tokens = getattr(practice_usage, "input_tokens", None)
                        if p_tokens is None:
                            p_tokens = getattr(practice_usage, "request_tokens", 0) or 0
                        c_tokens = getattr(practice_usage, "output_tokens", None)
                        if c_tokens is None:
                            c_tokens = getattr(practice_usage, "response_tokens", 0) or 0
                        tot_tokens = getattr(practice_usage, "total_tokens", 0) or (p_tokens + c_tokens)
                        if tot_tokens > 0:
                            spec = getattr(self._llm, "structured_model_name", getattr(self._llm, "_structured_model_name", "unknown"))
                            provider, model = spec.split(":", 1) if ":" in spec else ("unknown", spec)
                            est_cost = (p_tokens * 0.59 + c_tokens * 0.79) / 1_000_000.0
                            self._cache_repository.record_usage(
                                owner_id=owner_id,
                                provider=provider,
                                model=model,
                                prompt_tokens=p_tokens,
                                completion_tokens=c_tokens,
                                total_tokens=tot_tokens,
                                estimated_cost_usd=est_cost,
                            )
                    break # Success
                except DailyBudgetExceededError:
                    raise
                except Exception as e:
                    error_msg = str(e).lower()
                    if "429" in error_msg or "too many requests" in error_msg or "rate limit" in error_msg:
                        time.sleep(2 ** attempt)
                    elif "validation" in error_msg or "unexpectedmodelbehavior" in error_msg:
                        time.sleep(1)
                    else:
                        print(f"Failed to generate practice sentences for text {text_id}: {e}")
                        break
            else:
                print(f"Failed to generate practice sentences for text {text_id}: Max retries exceeded")
                
        # 3. Fetch Dictionary Translations for Top Words
        print("Fetching dictionary translations for top words...")
        def _fetch_dict_translation(freq):
            if not freq.translation:
                try:
                    translation = self._dictionary.translate_word(freq.word, record.language)
                    if translation:
                        freq.translation = translation
                        self._repository.update_word_frequency(freq)
                except Exception as e:
                    print(f"Failed to fetch translation for '{freq.word}': {e}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
            futures = [executor.submit(_fetch_dict_translation, freq) for freq in frequencies[:15]]
            concurrent.futures.wait(futures)

        # 4. Mark text as fully processed
        record.status = "processed"
        self._repository.update_text(record)
        if self._job_repository:
            jobs = self._job_repository.load_jobs_by_text(text_id, owner_id)
            for j in jobs:
                if j.id is not None and j.status in ("pending", "leased"):
                    self._job_repository.complete(j.id, j.worker_id or "local_worker")
        print(f"Successfully finished processing text '{record.title}' (ID: {text_id})!")
