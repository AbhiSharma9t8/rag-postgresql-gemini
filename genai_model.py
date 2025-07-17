import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables (assuming your API key is in a .env file)
load_dotenv()

# Configure the Gemini API with your API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file. Please add it.")

genai.configure(api_key=GEMINI_API_KEY)

print("Available Gemini models:")
# Iterate through all available models
for model in genai.list_models():
    # Print relevant information for each model
    print(f"Name: {model.name}")
    print(f"  Display Name: {model.display_name}")
    print(f"  Description: {model.description}")
    print(f"  Input Token Limit: {model.input_token_limit}")
    print(f"  Output Token Limit: {model.output_token_limit}")
    print(f"  Supported Generation Methods: {model.supported_generation_methods}")
    print("-" * 30)