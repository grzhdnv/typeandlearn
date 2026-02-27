"""
Text conversion between file formats
"""

import json

import nltk

nltk.download("punkt")  # Download sentence tokenizer
from nltk.tokenize import sent_tokenize


def text_to_json(book_name, sentence_type, json_path, sentences_input_path):
    """
    Convert text to JSON books format

    Inputs:
    --------
    book_name: String, Name of the book

    sentence_type: String, Type of sentences to add (generated or original)

    json_path: String, Path to the JSON file

    sentences_input_path: String, Path to the text file
    """
    # Read the text file
    with open(sentences_input_path, "r") as f:
        text = f.read()
    # Split into sentences
    paragraphs = text.split("\n\n")
    sentences = [s.strip() for para in paragraphs for s in sent_tokenize(para) if s.strip()]

    with open(json_path, "r+") as f:
        data = json.load(f)

        book_found = False
        # If book in JSON, update the sentences
        for book in data["books"]:
            if book["text_name"] == book_name:
                book[sentence_type] = sentences
                book_found = True
                break

        # If book not in JSON, add it
        if not book_found:
            new_book = {"text_name": book_name}
            new_book[sentence_type] = sentences
            data["books"].append(new_book)
            print(data)
    with open(json_path, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
