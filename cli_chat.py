# cli_chat.py
from llm import llm
import asyncio

async def main():
    print("Welcome to The Sentient Sip! (Type 'quit' to exit)")
    while True:
        user_input = input("You: ")
        if user_input.lower() == "quit":
            break
        response = await llm(user_input)
        print(f"Rita: {response}")

asyncio.run(main())