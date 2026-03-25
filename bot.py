import discord
from discord.ext import commands
from discord import app_commands, Interaction
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
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = CodeWeaver()

# --- HELPER: AI RESPONSE ---
async def get_ai_response(content):
    try:
        response = await asyncio.to_thread(
            g4f.ChatCompletion.create,
            model=g4f.models.gpt_4,
            messages=[
                {"role": "system", "content": "You are an elite AI assistant. Stay concise and helpful."},
                {"role": "user", "content": content}
            ]
        )
        return str(response)[:1950]
    except Exception:
        return "⚠️ The AI engine is currently processing other requests. Please try again in a moment."

# --- COMMAND: CHAT (Public Channel) ---
@bot.tree.command(name="chat", description="Ask the AI anything in this channel")
async def chat(itx: Interaction, message: str):
    await itx.response.defer()
    answer = await get_ai_response(message)
    await itx.followup.send(f"💻 **AI Response:**\n{answer}")

# --- COMMAND: CLEAR ---
@bot.tree.command(name="clear", description="Delete a specified number of messages")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(itx: Interaction, amount: int):
    await itx.response.defer(ephemeral=True)
    deleted = await itx.channel.purge(limit=amount)
    await itx.followup.send(f"✅ Successfully cleared {len(deleted)} messages.")

# --- FEATURE: DM AI CHAT ---
@bot.event
async def on_message(message):
    # Ignore bot's own messages
    if message.author == bot.user:
        return

    # Check if the message is a Private Message (DM)
    if isinstance(message.channel, discord.DMChannel):
        async with message.channel.typing():
            answer = await get_ai_response(message.content)
            await message.author.send(f"🤖 **Private AI Assistant:**\n{answer}")

    await bot.process_commands(message)

# --- STARTUP LOGIC ---
def run_production_server():
    port = int(os.environ.get("PORT", 8080))
    # Production server (Waitress) is silent and warning-free
    serve(app, host='0.0.0.0', port=port, _quiet=True)

@bot.event
async def on_ready():
    print(f"💎 Code Weaver V11: Logged in as {bot.user}")
    print("🚀 All systems online. Console is clear.")

if __name__ == "__main__":
    if not TOKEN:
        print("❌ ERROR: DISCORD_TOKEN is missing in Railway Variables.")
    else:
        # Launch silent web server in background
        Thread(target=run_production_server, daemon=True).start()
        # Launch Bot
        bot.run(TOKEN)
