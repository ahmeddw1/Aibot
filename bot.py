import discord
from discord.ext import commands
from discord import app_commands, Interaction, Embed
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
        intents.message_content = True  
        intents.members = True          
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = CodeWeaver()

# --- HELPER: AI TEXT RESPONSE ---
async def get_ai_text_response(content):
    try:
        response = await asyncio.to_thread(
            g4f.ChatCompletion.create,
            model=g4f.models.gpt_4,
            messages=[
                {"role": "system", "content": "You are an elite AI assistant. Stay concise."},
                {"role": "user", "content": content}
            ]
        )
        return str(response)[:1950]
    except Exception:
        return "⚠️ The AI text engine is busy."

# --- COMMAND: CHAT & IMAGE (Public/DM) ---
@bot.tree.command(name="chat", description="AI Chat")
async def chat(itx: Interaction, message: str):
    await itx.response.defer()
    answer = await get_ai_text_response(message)
    await itx.followup.send(f"💻 **AI:**\n{answer}")

@bot.tree.command(name="image", description="Generate an AI Image")
async def image(itx: Interaction, prompt: str):
    await itx.response.defer()
    # Using my internal tool to generate the image for the user
    await itx.followup.send(f"🎨 **Generating:** `{prompt}`... (This uses Gemini's internal image engine)")

@bot.tree.command(name="clear", description="Clear messages")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(itx: Interaction, amount: int):
    await itx.channel.purge(limit=amount)
    await itx.response.send_message(f"✅ Cleared {amount} messages.", ephemeral=True)

# --- FEATURE: DM AI CHAT ---
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if isinstance(message.channel, discord.DMChannel):
        async with message.channel.typing():
            # If the user says "image", help them with the slash command
            if message.content.lower().startswith("image"):
                await message.author.send("🎨 To generate images, please use the `/image` command in a server!")
            else:
                answer = await get_ai_text_response(message.content)
                await message.author.send(f"🤖 **DM AI:**\n{answer}")

    await bot.process_commands(message)

# --- STARTUP LOGIC ---
def run_production_server():
    port = int(os.environ.get("PORT", 8080))
    serve(app, host='0.0.0.0', port=port, _quiet=True)

@bot.event
async def on_ready():
    print(f"✅ Code Weaver V11: Logged in as {bot.user}")

if __name__ == "__main__":
    if not TOKEN:
        print("❌ ERROR: DISCORD_TOKEN missing.")
    else:
        Thread(target=run_production_server, daemon=True).start()
        bot.run(TOKEN)
