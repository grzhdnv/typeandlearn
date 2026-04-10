from dotenv import load_dotenv
from google import genai
import os
from pydantic import BaseModel, ValidationError
from typing import List, Dict


# Pydantic models for validation
class Sentence(BaseModel):
    index: int
    text: str
    translation: str
    translation_hints: Dict[str, str]


class Paragraph(BaseModel):
    index: int
    sentences: List[Sentence]


class PracticeSentence(BaseModel):
    index: int
    sentence: str
    translation: str
    translation_hints: Dict[str, str]


class TextData(BaseModel):
    title: str
    original_paragraphs: List[Paragraph]
    practice_sentences: List[PracticeSentence]


# Load environment variables from .env file
load_dotenv()

# Set the file path and prompt path
file_path = "./backend/data/texts/20141246.txt"
prompt_path = "./backend/prompts/text_to_db.md"

# Set the model name
model = "gemini-3-flash-preview"

with open(file_path, "r") as file:
    input_text = file.read()

with open(prompt_path, "r") as file:
    prompt = file.read()


# Initialize the GenAI client with the google API key
client = genai.Client(api_key=os.getenv("GOOGLE_GENAI_API_KEY"))


# Generate text using the Gemini model
# Validate the response with Pydantic and save the generated text to a JSON file
def text_to_db(
    input_text,
    client=client,
    model=model,
    prompt=prompt,
):
    try:
        print("Generating content...")
        response = client.models.generate_content(
            model=model,
            contents=[prompt, input_text],
        )

        print("Content generated successfully!\n")
        print(response.text)  # This will print the raw JSON response from the model

        # strip the response to get the only contents inside {...}
        jsonified_response = response.text[
            response.text.find("{") : response.text.rfind("}") + 1
        ]

        # Parse and validate with Pydantic
        data = TextData.model_validate_json(jsonified_response)
        print("Validation successful!")

        return data

    # Handle any exceptions that may occur during the API call or validation
    except ValidationError as ve:
        print(f"Pydantic Validation Error: {ve}")
    except Exception as e:
        print(f"Error: {e}")


# def translate_to_english(text, prompt="Translate the given text to English."):
#     try:
#         response = client.models.generate_content(
#             model=model,
#             contents=[prompt, text],
#         )
#         return response.text
#     except Exception as e:
#         print(f"Error during translation: {e}")
#         return None


def main():
    # Example usage of the translation function
    text_to_db(input_text)


if __name__ == "__main__":
    main()
