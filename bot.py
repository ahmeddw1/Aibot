import discord
from discord.ext import commands
from discord import app_commands, Interaction, File
import os
import io
import asyncio
import logging
import re
import g4f
from flask import Flask
from threading import Thread
from waitress import serve
from dotenv import load_dotenv

# --- INITIALIZATION ---
load_dotenv()
logging.getLogger('waitress').setLevel(logging.ERROR)
logging.getLogger('werkzeug').setLevel(logging.ERROR)

app = Flask(__name__)
@app.route('/')
def health(): return "Ironclad System: Online", 200

# --- CONFIGURATION ---
TOKEN = os.environ.get("DISCORD_TOKEN")
# Replace this with your actual Channel ID where the bot should auto-respond
AI_CHANNEL_ID = 1486037466850001118

class CodeWeaver(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self):
        # Syncs slash commands like /chat
        await self.tree.sync()

bot = CodeWeaver()

# --- UTILITY: CODE TO FILE ENGINE ---
def process_code_to_files(text):
    if not text:
        return "⚠️ No response generated.", []
        
    regex = r"```(\w+)?\n([\s\S]*?)```"
    matches = re.findall(regex, text)
    files = []
    
    ext_map = {
        "python": "py", "py": "py", "javascript": "js", "js": "js", 
        "node": "js", "java": "java", "html": "html", "css": "css", "cpp": "cpp"
    }

    for i, (lang, code) in enumerate(matches):
        lang = lang.lower() if lang else "txt"
        extension = ext_map.get(lang, "txt")
        # Use io.BytesIO to create an in-memory file
        stream = io.BytesIO(code.encode('utf-8'))
        files.append(File(fp=stream, filename=f"exported_code_{i+1}.{extension}"))
    
    clean_text = re.sub(regex, "*(Code file generated below)*", text)
    return clean_text, files

# --- FREE AI LOGIC ---
async def get_free_ai_response(prompt):
    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(
                g4f.ChatCompletion.create,
                model=g4f.models.gpt_4,
                messages=[{"role": "user", "content": prompt}],
            ), timeout=45.0 # Increased timeout for stability
        )
        return process_code_to_files(str(response))
    except asyncio.TimeoutError:
        return "⚠️ The AI is taking too long to respond. Providers might be busy.", []
    except Exception as e:
        print(f"AI Provider Error: {e}")
        return "⚠️ Free AI provider is currently offline. Please try again shortly.", []

# --- SLASH COMMANDS ---

@bot.tree.command(name="chat", description="Ask the AI a question")
async def chat(itx: Interaction, message: str):
    await itx.response.defer() # Gives AI time to think
    text, files = await get_free_ai_response(message)
    try:
        # Discord limit is 2000 chars; cutting at 1950 for safety
        await itx.followup.send(text[:1950], files=files)
    except Exception as e:
        print(f"Chat Send Error: {e}")

@bot.tree.command(name="clear", description="Delete messages")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(itx: Interaction, amount: int):
    await itx.channel.purge(limit=amount)
    await itx.response.send_message(f"🧹 Cleared {amount} messages.", ephemeral=True)

# --- AUTO-RESPONDER & DM HANDLER ---

@bot.event
async def on_message(msg):
    # Don't respond to itself
    if msg.author == bot.user:
        return

    # Check if message is in the AI Channel OR is a DM
    is_ai_channel = msg.channel.id == AI_CHANNEL_ID
    is_dm = isinstance(msg.channel, discord.DMChannel)

    if is_ai_channel or is_dm:
        async with msg.channel.typing():
            text, files = await get_free_ai_response(msg.content)
            
            # 503/Server Error Retry Logic
            for attempt in range(3):
                try:
                    await msg.reply(text[:1950], files=files)
                    break 
                except discord.errors.DiscordServerError:
                    if attempt < 2:
                        await asyncio.sleep(2)
                        continue
                except Exception as e:
                    print(f"Message Send Error: {e}")
                    break

    await bot.process_commands(msg)

# --- WEB SERVER & STARTUP ---

def run_web():
    # Bind to PORT provided by Render, default to 8080
    port = int(os.environ.get("PORT", 8080))
    serve(app, host='0.0.0.0', port=port, _quiet=True)

@bot.event
async def on_ready():
    print(f"✅ Logged in as: {bot.user}")
    print(f"🚀 Monitoring Channel ID: {AI_CHANNEL_ID}")
    print("💎 Slash commands synced and AI logic online.")

if __name__ == "__main__":
    if TOKEN:
        # Start the health-check server for Render
        Thread(target=run_web, daemon=True).start()
        bot.run(TOKEN)
    else:
        print("❌ ERROR: DISCORD_TOKEN is missing in your environment!")
