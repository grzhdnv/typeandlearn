from pathlib import Path
import json

DATA_DIR = Path("backend/data")
DATA_FILE = DATA_DIR / "db.json"


def load_data() -> list[dict]:
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            content: str = f.read()
            if content.strip():
                loaded = json.loads(content)
                if isinstance(loaded, list):
                    return loaded
                if isinstance(loaded, dict):
                    return [loaded]
    return []


def save_data(data: list[dict]) -> None:
    # saves the data to the JSON file, in [{}, {...}] format
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# --- for testing --- #


def main():
    # test load_data
    data = load_data()
    # print type of data
    print("Loaded data:", type(data))
    print("Loaded data:", data)


if __name__ == "__main__":
    main()
