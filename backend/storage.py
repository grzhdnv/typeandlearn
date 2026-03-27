from pathlib import Path
import json

DATA_DIR = Path("backend/data")
DATA_FILE = DATA_DIR / "texts_db.json"


def load_data() -> list[dict]:
    if DATA_FILE.exists():
        with open(DATA_FILE, "r") as f:
            content: str = f.read()
            if content.strip():
                return json.loads(content)
    return []


def save_data(data: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


print(load_data())
