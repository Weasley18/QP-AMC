import base64
import os
from google import genai
from google.genai import types

def generate_from_pdf(pdf_file_path: str):
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    model = "gemini-2.5-flash-preview-04-17"  # Your specified model

    # Read the PDF file in binary mode
    with open(pdf_file_path, "rb") as f:
        pdf_bytes = f.read()

    # Create a Part from the PDF bytes
    pdf_part = types.Part.from_bytes(mime_type="application/pdf", data=pdf_bytes)

    contents = [
        types.Content(
            role="user",
            parts=[
                pdf_part,
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        response_mime_type="application/json",  # Changed to application/json as per your system instruction
        system_instruction=[
            types.Part.from_text(text="""You will be given a pdf of notes: Handwritten or Typed.
        Your task is to convert handwritten notes to clear text .
        If the pdf is in typed format , just parse the text.
        The return should be a json file with the fields: subject, topics, text.
        Structure the JSON output with proper readability for formulas and examples."""),
        ],
    )

    print(f"Generating content from PDF: {pdf_file_path} using model {model}")
    try:
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            print(chunk.text, end="")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Replace "path/to/your/notes.pdf" with the actual path to your PDF file
    pdf_path = "/Users/chethanar/QP-AMC/ada_mod2.pdf"
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found at {pdf_path}")
    else:
        generate_from_pdf(pdf_path)