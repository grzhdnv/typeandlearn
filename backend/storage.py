from pathlib import Path
import json

DATA_DIR = Path("backend/data")
DATA_FILE = DATA_DIR / "db.json"


def load_data() -> list[dict]:
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            content: str = f.read()
            if content.strip():
                return json.loads(content)
    return []


def save_data(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
