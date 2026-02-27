from dotenv import load_dotenv
from google import genai
import os

# Load environment variables from .env file
load_dotenv()

# Set the file path and prompt path
file_path = "./test_files/freq_table_prompt.md"
prompt_path = "./test_files/prompt.md"

# Set the model name
model = "gemini-3-flash-preview"

with open(file_path, "r") as file:
    input_text = file.read()

with open(prompt_path, "r") as file:
    prompt = file.read()


# Initialize the GenAI client with the google API key
client = genai.Client(api_key=os.getenv("GOOGLE_GENAI_API_KEY"))

# Generate text using the Gemini model
try:
    print("Generating content...")
    response = client.models.generate_content(
        model=model,
        contents=[prompt, input_text],
    )
    print(response.text)
    exit(0)
# Handle any exceptions that may occur during the API call
# Common exceptions include 503 UNAVAILABLE and 429 TOO_MANY_REQUESTS
except Exception as e:
    print(e)
    exit(1)
