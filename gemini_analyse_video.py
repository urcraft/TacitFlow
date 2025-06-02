import os
from google import genai

api_key = os.environ.get("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

myfile = client.files.upload(file="./test.mp3")

response = client.models.generate_content(
    model="gemini-2.0-flash", contents=["Transcribe this audio clip", myfile]
)

print(response.text)