"""
Validate uploaded file, convert to usable version if needed
"""

from pathlib import Path


def convert_pdf_to_text(filename: str) -> str:
    """
    Convert PDF file to text
    """

    _ = filename
    raise NotImplementedError("PDF conversion not implemented yet")


def validate_file(filename: str) -> str:
    """
    Validate uploaded file

    Return plaintext representation of file
    """
    extension = filename.split(".", maxsplit=1)[1].lower()
    file = Path(filename)
    if not file.is_file():
        raise FileNotFoundError(f"File {filename} not found")
    if extension == "pdf":
        return convert_pdf_to_text(filename)
    if extension in ["md", "txt"]:
        with file.open(encoding="utf-8") as f:
            return f.read()
    return ""  # invalid file


def process_file(filename: str) -> bool:
    """
    Process uploaded file, convert to usable version if needed
    """
    # store text?
    return bool(validate_file(filename))


if __name__ == "__main__":
    print(process_file(input("Enter file name: ")))  # noqa: T201
