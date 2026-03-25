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

# --- 1. SILENT PRODUCTION SERVER ---
logging.getLogger('waitress').setLevel(logging.ERROR)
logging.getLogger('werkzeug').setLevel(logging.ERROR)
os.environ['WERKZEUG_RUN_MAIN'] = 'true'

app = Flask(__name__)
@app.route('/')
def health(): return "Code Weaver V11: Online", 200

# --- 2. BOT CONFIGURATION ---
TOKEN = os.environ.get("DISCORD_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

# Configure Gemini
genai.configure(api_key=GEMINI_KEY)
chat_model = genai.GenerativeModel('gemini-1.5-flash')

class CodeWeaver(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self):
        await self.tree.sync()

bot = CodeWeaver()

# --- 3. CORE LOGIC FUNCTIONS ---

async def get_ai_chat(prompt):
    try:
        response = await asyncio.to_thread(chat_model.generate_content, prompt)
        return response.text[:1950]
    except Exception as e:
        return f"⚠️ Chat Error: {str(e)}"

async def get_ai_image(prompt):
    try:
        # Using a reliable image generation API that Discord can embed immediately
        encoded_prompt = prompt.replace(" ", "%20")
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?nologo=true&width=1024&height=1024"
        
        # Download the actual image bytes
        response = await asyncio.to_thread(requests.get, url, timeout=15)
        if response.status_code == 200:
            return io.BytesIO(response.content)
        return None
    except Exception:
        return None

# --- 4. SLASH COMMANDS ---

@bot.tree.command(name="chat", description="Chat with Gemini Pro AI")
async def chat(itx: Interaction, message: str):
    await itx.response.defer()
    reply = await get_ai_chat(message)
    await itx.followup.send(f"♊ **AI:** {reply}")

@bot.tree.command(name="image", description="Generate a visible AI image")
async def image(itx: Interaction, prompt: str):
    await itx.response.defer()
    img_buffer = await get_ai_image(prompt)
    if img_buffer:
        file = File(fp=img_buffer, filename="weaver_art.png")
        await itx.followup.send(content=f"🎨 **Prompt:** `{prompt}`", file=file)
    else:
        await itx.followup.send("❌ Failed to generate image.")

@bot.tree.command(name="clear", description="Purge messages from channel")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(itx: Interaction, amount: int):
    await itx.channel.purge(limit=amount)
    await itx.response.send_message(f"🧹 Cleared {amount} messages.", ephemeral=True)

# --- 5. SMART DM HANDLER ---

@bot.event
async def on_message(msg):
    if msg.author == bot.user:
        return

    # Handle Private Messages (DMs)
    if isinstance(msg.channel, discord.DMChannel):
        async with msg.channel.typing():
            content = msg.content.lower()
            # If user asks to draw or generate in DM
            if any(word in content for word in ["draw", "image", "generate", "art"]):
                img_buffer = await get_ai_image(msg.content)
                if img_buffer:
                    await msg.author.send(file=File(fp=img_buffer, filename="dm_art.png"))
                else:
                    await msg.author.send("⚠️ I couldn't generate that image.")
            else:
                reply = await get_ai_chat(msg.content)
                await msg.author.send(f"🤖 **DM AI:** {reply}")

    await bot.process_commands(msg)

# --- 6. STARTUP ---

def run_web():
    port = int(os.environ.get("PORT", 8080))
    serve(app, host='0.0.0.0', port=port, _quiet=True)

@bot.event
async def on_ready():
    print(f"✅ Code Weaver V11 Online | Logged in as: {bot.user}")

if __name__ == "__main__":
    if not TOKEN or not GEMINI_KEY:
        print("❌ CRITICAL ERROR: DISCORD_TOKEN or GEMINI_API_KEY is missing!")
    else:
        Thread(target=run_web, daemon=True).start()
        bot.run(TOKEN)
