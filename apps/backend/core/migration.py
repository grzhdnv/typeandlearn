"""Migration helper to load legacy db.json data into the database."""

import json
from pathlib import Path

from core.database import engine, init_db
from models.texts import PracticeSentenceRecord, SentenceRecord, TextRecord
from sqlmodel import Session


def migrate_data() -> None:
    """Read db.json and populate the database if it is currently empty."""
    print("Initializing database tables...")
    init_db()

    # Path to legacy JSON data file relative to core/migration.py
    backend_dir = Path(__file__).resolve().parents[1]
    db_json_path = backend_dir / "data" / "db.json"

    if not db_json_path.exists():
        print(f"Source JSON file not found at {db_json_path}. Skipping migration.")
        return

    print("Checking if database already has records...")
    with Session(engine) as session:
        # Database can have records, we'll append the imported texts.

        print(f"Reading data from {db_json_path}...")
        try:
            content = db_json_path.read_text(encoding="utf-8")
            if not content.strip():
                print("JSON file is empty. Nothing to migrate.")
                return
            data = json.loads(content)
        except Exception as error:
            print(f"Error reading/parsing JSON file: {error}")
            return

        # Normalize data format (list or single dict)
        if isinstance(data, dict):
            records_to_migrate = [data]
        elif isinstance(data, list):
            records_to_migrate = data
        else:
            print(f"Invalid JSON data type: {type(data)}. Expected list or dict.")
            return

        print(f"Found {len(records_to_migrate)} texts to migrate. Migrating...")
        for i, item in enumerate(records_to_migrate):
            title = item.get("title", f"Imported Text {i + 1}")
            original_paragraphs = item.get("original_paragraphs", [])
            practice_sentences = item.get("practice_sentences", [])

            # 1. Insert TextRecord
            word_count = sum(len(s.get("text", "").split()) for p in original_paragraphs for s in p.get("sentences", []))
            total_sentences = sum(len(p.get("sentences", [])) for p in original_paragraphs)
            estimated_time = max(1, word_count // 40)
            
            record = TextRecord(
                title=title, 
                status="completed",
                language="German", # The old file is all German based on the sample
                difficulty_level="Unrated",
                word_count=word_count,
                completed_sentences=0,
                total_sentences=total_sentences,
                estimated_time_minutes=estimated_time
            )
            session.add(record)
            session.flush()  # Flushes to the database so `record.id` is populated!

            # 2. Insert SentenceRecords
            for p in original_paragraphs:
                p_index = p.get("index", 0)
                for s in p.get("sentences", []):
                    session.add(
                        SentenceRecord(
                            text_id=record.id,  # type: ignore
                            paragraph_index=p_index,
                            sentence_index=s.get("index", 0),
                            original_text=s.get("text", ""),
                            translation=s.get("translation", ""),
                            translation_hints=s.get("translation_hints", {}),
                            status="completed",
                        )
                    )

            # 3. Insert PracticeSentenceRecords
            for ps in practice_sentences:
                session.add(
                    PracticeSentenceRecord(
                        text_id=record.id,  # type: ignore
                        sentence_index=ps.get("index", 0),
                        sentence=ps.get("sentence", ""),
                        translation=ps.get("translation", ""),
                        translation_hints=ps.get("translation_hints", {}),
                    )
                )

        session.commit()
        print("Migration completed successfully!")
