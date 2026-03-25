import discord
from discord.ext import commands
from discord import app_commands, Interaction, File
import os
import io
import asyncio
import logging
from google import genai
from google.genai import types
from flask import Flask
from threading import Thread
from waitress import serve

# --- 1. SILENT PRODUCTION SERVER ---
logging.getLogger('waitress').setLevel(logging.ERROR)
logging.getLogger('werkzeug').setLevel(logging.ERROR)

app = Flask(__name__)
@app.route('/')
def health(): return "System Status: Online", 200

# --- 2. GOOGLE GENAI CLIENT SETUP ---
# It automatically looks for GEMINI_API_KEY in environment variables
client = genai.Client()

class CodeWeaver(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self):
        await self.tree.sync()

bot = CodeWeaver()

# --- 3. AI LOGIC FUNCTIONS ---

async def get_gemini_chat(prompt):
    try:
        # Using the new SDK generate_content method
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-3-flash-preview",
            contents=prompt
        )
        return response.text[:1950]
    except Exception as e:
        return f"⚠️ Chat Error: {str(e)}"

async def get_gemini_image(prompt):
    try:
        # Using the new SDK for image generation
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-3.1-flash-image-preview",
            contents=[prompt]
        )
        
        for part in response.parts:
            if part.inline_data is not None:
                # Convert the part to an image and save to buffer
                image = part.as_image()
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)
                return img_byte_arr
        return None
    except Exception as e:
        print(f"Image Error: {e}")
        return None

# --- 4. SLASH COMMANDS ---

@bot.tree.command(name="chat", description="Chat with Gemini 3 Flash")
async def chat(itx: Interaction, message: str):
    await itx.response.defer()
    reply = await get_gemini_chat(message)
    await itx.followup.send(f"♊ **AI:** {reply}")

@bot.tree.command(name="image", description="Generate image with Gemini 3.1")
async def image(itx: Interaction, prompt: str):
    await itx.response.defer()
    img_buffer = await get_gemini_image(prompt)
    if img_buffer:
        file = File(fp=img_buffer, filename="gemini_gen.png")
        await itx.followup.send(content=f"🎨 **Generated:** `{prompt}`", file=file)
    else:
        await itx.followup.send("❌ Failed to generate image. Check your API permissions.")

@bot.tree.command(name="clear", description="Clear channel messages")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(itx: Interaction, amount: int):
    await itx.channel.purge(limit=amount)
    await itx.response.send_message(f"🧹 Cleared {amount} messages.", ephemeral=True)

# --- 5. SMART DM HANDLER ---

@bot.event
async def on_message(msg):
    if msg.author == bot.user: return

    if isinstance(msg.channel, discord.DMChannel):
        async with msg.channel.typing():
            content = msg.content.lower()
            if any(k in content for k in ["draw", "image", "generate", "art"]):
                img_buffer = await get_gemini_image(msg.content)
                if img_buffer:
                    await msg.author.send(file=File(fp=img_buffer, filename="dm_art.png"))
                else:
                    await msg.author.send("⚠️ Image generation failed.")
            else:
                reply = await get_gemini_chat(msg.content)
                await msg.author.send(f"🤖 **DM AI:** {reply}")

    await bot.process_commands(msg)

# --- 6. EXECUTION ---

def run_web():
    port = int(os.environ.get("PORT", 8080))
    serve(app, host='0.0.0.0', port=port, _quiet=True)

@bot.event
async def on_ready():
    print(f"✅ Code Weaver V11 [New SDK] Online as: {bot.user}")

if __name__ == "__main__":
    TOKEN = os.environ.get("DISCORD_TOKEN")
    if not TOKEN or not os.environ.get("GEMINI_API_KEY"):
        print("❌ ERROR: Tokens missing in environment variables!")
    else:
        Thread(target=run_web, daemon=True).start()
        bot.run(TOKEN)
