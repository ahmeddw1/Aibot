import discord
from discord.ext import commands
from discord import app_commands, Interaction, File
import os
import io
import asyncio
import requests
import logging
import google.generativeai as genai
from flask import Flask
from threading import Thread
from waitress import serve

# --- SILENCE WEB LOGS ---
logging.getLogger('waitress').setLevel(logging.ERROR)
logging.getLogger('werkzeug').setLevel(logging.ERROR)

app = Flask(__name__)
@app.route('/')
def health(): return "System Status: Online", 200

# --- CONFIGURATION ---
TOKEN = os.environ.get("DISCORD_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

# Setup Gemini
genai.configure(api_key=GEMINI_KEY)
# Using 'gemini-1.5-flash' for text and 'imagen-3' (if available in your region) for images
text_model = genai.GenerativeModel('gemini-1.5-flash')
# Note: Gemini's image generation is usually handled via the 'imagen' model 
# which may require specific project permissions. 
# We will use the official generation flow.

class CodeWeaver(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = CodeWeaver()

# --- GEMINI AI LOGIC ---
async def get_gemini_text(prompt):
    try:
        response = await asyncio.to_thread(text_model.generate_content, prompt)
        return response.text[:1950]
    except Exception as e:
        return f"⚠️ Gemini Text Error: {str(e)}"

async def get_gemini_image(prompt):
    """
    Note: Direct Imagen-3 access via the Gemini API varies by region/tier.
    This structure uses the Google generative AI flow.
    """
    try:
        # We call the generation model. 
        # If your API key has Imagen access, this will return image data.
        model = genai.GenerativeModel('imagen-3') # Or 'google/imagen-3-001'
        result = await asyncio.to_thread(model.generate_content, prompt)
        
        # Extract the image bytes from the response
        image_bytes = result.candidates[0].content.parts[0].inline_data.data
        return io.BytesIO(image_bytes)
    except Exception:
        # Fallback to a high-quality API if Imagen is restricted on your specific key
        fallback_url = f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}?nologo=true"
        img_data = requests.get(fallback_url).content
        return io.BytesIO(img_data)

# --- COMMANDS ---
@bot.tree.command(name="chat", description="Chat with Gemini AI")
async def chat(itx: Interaction, message: str):
    await itx.response.defer()
    response = await get_gemini_text(message)
    await itx.followup.send(f"♊ **Gemini:** {response}")

@bot.tree.command(name="image", description="Generate Image via Gemini")
async def image(itx: Interaction, prompt: str):
    await itx.response.defer()
    img_buffer = await get_gemini_image(prompt)
    file = File(fp=img_buffer, filename="gemini_art.png")
    await itx.followup.send(content=f"🎨 **Prompt:** `{prompt}`", file=file)

@bot.tree.command(name="clear", description="Clear messages")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(itx: Interaction, amount: int):
    await itx.channel.purge(limit=amount)
    await itx.response.send_message(f"🧹 Cleared {amount} messages.", ephemeral=True)

# --- DM SUPPORT ---
@bot.event
async def on_message(msg):
    if msg.author == bot.user: return
    if isinstance(msg.channel, discord.DMChannel):
        async with msg.channel.typing():
            content = msg.content.lower()
            # If they ask for an image/drawing in DM
            if any(word in content for word in ["draw", "image", "generate", "art"]):
                img_buffer = await get_gemini_image(msg.content)
                await msg.author.send(file=File(fp=img_buffer, filename="dm_art.png"))
            else:
                response = await get_gemini_text(msg.content)
                await msg.author.send(f"♊ **Gemini DM:** {response}")

# --- RAILWAY STARTUP ---
def run_web():
    port = int(os.environ.get("PORT", 8080))
    serve(app, host='0.0.0.0', port=port, _quiet=True)

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    if TOKEN:
        print("💎 Code Weaver V11 [Gemini Edition] Online.")
        bot.run(TOKEN)
