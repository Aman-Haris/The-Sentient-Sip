import os  
import asyncio
from mistralai import Mistral
from prompt import get_system_prompt
from gtts import gTTS
from playsound import playsound
import os
import tempfile
  
# Load environment variables
Temperature = float(os.getenv("Temperature"))  
Top_P = float(os.getenv("Top_P"))  
Max_Tokens = int(os.getenv("Max_Tokens"))  
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

async def invoke_model(user_input, chat_history=None):
    model = "mistral-large-latest"
    client = Mistral(api_key=MISTRAL_API_KEY)
    
    # Prepare messages list
    messages = [
        {"role": "system", "content": get_system_prompt(chat_history)},
    ]
    
    # Add chat history if available
    if chat_history:
        for message in chat_history:
            messages.append({"role": message["role"], "content": message["content"]})
    
    # Add current user input
    messages.append({"role": "user", "content": user_input})
    
    chat_response = await client.chat.complete_async(
        model=model,
        messages=messages,
        temperature=Temperature,
        top_p=Top_P,
        max_tokens=Max_Tokens
    )
    return chat_response.choices[0].message.content.strip()

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