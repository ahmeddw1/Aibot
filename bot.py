import discord
from discord.ext import commands
from discord import app_commands, Interaction, File
import os
import asyncio
import logging
from flask import Flask
from threading import Thread
from waitress import serve
import g4f

# --- SILENCE ALL WEB LOGS ---
logging.getLogger('waitress').setLevel(logging.ERROR)
logging.getLogger('werkzeug').setLevel(logging.ERROR)
os.environ['WERKZEUG_RUN_MAIN'] = 'true'

app = Flask(__name__)

@app.route('/')
def health():
    return "System Status: Online", 200

# --- BOT ENGINE ---
TOKEN = os.environ.get("DISCORD_TOKEN")

class CodeWeaver(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True  # Required for DM and Channel Reading
        intents.members = True          # Required for some member-related ops, good to have
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = CodeWeaver()

# --- HELPER: AI TEXT RESPONSE ---
async def get_ai_text_response(content):
    try:
        response = await asyncio.to_thread(
            g4f.ChatCompletion.create,
            model=g4f.models.gpt_4, # Using GPT-4 equivalent for chat
            messages=[
                {"role": "system", "content": "You are an elite AI assistant. Stay concise and helpful."},
                {"role": "user", "content": content}
            ]
        )
        return str(response)[:1950]
    except Exception:
        return "⚠️ The AI text engine is busy. Please try again."

# --- HELPER: AI IMAGE GENERATION (Placeholder) ---
# NOTE: g4f doesn't directly support image generation.
# For actual image generation, you'd integrate with a service like DALL-E, Stable Diffusion API, etc.
# This function is a placeholder that simulates image generation.
async def generate_ai_image(prompt):
    try:
        # In a real scenario, you'd make an API call here.
        # Example with a hypothetical DALL-E 3 integration:
        # client = OpenAI(api_key="YOUR_OPENAI_API_KEY")
        # response = client.images.generate(model="dall-e-3", prompt=prompt, n=1, size="1024x1024")
        # image_url = response.data[0].url
        # download_image_to_file(image_url, "generated_image.png") # function to download from URL

        # For demonstration: generate a placeholder image using AI (text-based image generation)
        print(f"DEBUG: Attempting to generate image for prompt: {prompt}")
        image_description = await asyncio.to_thread(
            g4f.ChatCompletion.create,
            model=g4f.models.gpt_3_5_turbo, # Using a fast model for generating image concept
            messages=[
                {"role": "system", "content": "Describe a simple, visually interesting image based on the user's prompt, suitable for a logo or abstract art. Keep it brief."},
                {"role": "user", "content": prompt}
            ]
        )
        # Instead of a real image, we'll return a textual description.
        # In a real bot, you'd replace this with actual image data.
        return f"http://googleusercontent.com/image_generation_content/1
