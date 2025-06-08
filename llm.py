import os  
import asyncio
from mistralai import Mistral
from prompt import get_system_prompt
  
# Load environment variables
Temperature = float(os.getenv("Temperature"))  
Top_P = float(os.getenv("Top_P"))  
Max_Tokens = int(os.getenv("Max_Tokens"))  
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

async def llm(user_input):
    model = "mistral-large-latest"
    client = Mistral(api_key=MISTRAL_API_KEY)
    chat_response = await client.chat.complete_async(
        model=model,
        messages=[
            {"role": "system", "content": get_system_prompt()},
            {"role": "user", "content": user_input},
        ],
        temperature=Temperature,
        top_p=Top_P,
        max_tokens=Max_Tokens
    )
    return chat_response.choices[0].message.content.strip()

from gtts import gTTS
from playsound import playsound
import os
import tempfile

async def speak(text: str):
    """Convert text to speech using gTTS and play it."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fp:
            tts = gTTS(text=text, lang="en", slow=False)
            tts.save(fp.name)
            playsound(fp.name)
        os.unlink(fp.name)  # Clean up
    except Exception as e:
        print(f"Voice error: {e}")  # Fallback to text-only