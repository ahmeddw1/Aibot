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

# --- BOT SETUP ---
TOKEN = os.environ.get("DISCORD_TOKEN")

class CodeWeaver(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self):
        await self.tree.sync()

bot = CodeWeaver()

# --- UTILITY: CODE TO FILE ENGINE ---
def process_code_to_files(text):
    regex = r"```(\w+)\n([\s\S]*?)```"
    matches = re.findall(regex, text)
    files = []
    
    ext_map = {
        "python": "py", "py": "py", "javascript": "js", "js": "js", 
        "node": "js", "java": "java", "html": "html", "css": "css"
    }

    for i, (lang, code) in enumerate(matches):
        extension = ext_map.get(lang.lower(), "txt")
        # Ensure we reset the stream for every file
        stream = io.BytesIO(code.encode('utf-8'))
        files.append(File(fp=stream, filename=f"exported_code_{i+1}.{extension}"))
    
    clean_text = re.sub(regex, "*(Code file generated below)*", text)
    return clean_text, files

# --- FREE AI LOGIC ---
async def get_free_ai_response(prompt):
    try:
        # Using a timeout to prevent the bot from hanging
        response = await asyncio.wait_for(
            asyncio.to_thread(
                g4f.ChatCompletion.create,
                model=g4f.models.gpt_4,
                messages=[{"role": "user", "content": prompt}],
            ), timeout=30.0
        )
        return process_code_to_files(str(response))
    except asyncio.TimeoutError:
        return "⚠️ The AI is taking too long to respond. Please try a shorter prompt.", []
    except Exception:
        return "⚠️ Free AI provider is currently offline. Please try again in 1 minute.", []

# --- COMMANDS ---

@bot.tree.command(name="chat", description="AI Chat with code file support")
async def chat(itx: Interaction, message: str):
    await itx.response.defer()
    text, files = await get_free_ai_response(message)
    try:
        await itx.followup.send(text[:1950], files=files)
    except Exception as e:
        print(f"Chat Send Error: {e}")

@bot.tree.command(name="clear", description="Delete messages")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(itx: Interaction, amount: int):
    await itx.channel.purge(limit=amount)
    await itx.response.send_message(f"🧹 Done.", ephemeral=True)

# --- DM HANDLER (With 503/Timeout Fix) ---

@bot.event
async def on_message(msg):
    if msg.author == bot.user: return

    if isinstance(msg.channel, discord.DMChannel):
        async with msg.channel.typing():
            text, files = await get_free_ai_response(msg.content)
            
            # Retry logic for Discord Server Errors (503 fix)
            for attempt in range(3):
                try:
                    await msg.author.send(text[:1950], files=files)
                    break # Success!
                except discord.errors.DiscordServerError:
                    if attempt < 2:
                        await asyncio.sleep(2) # Wait 2 seconds and try again
                        continue
                except Exception as e:
                    print(f"DM Fatal Error: {e}")
                    break

    await bot.process_commands(msg)

# --- STARTUP ---

def run_web():
    serve(app, host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), _quiet=True)

@bot.event
async def on_ready():
    print(f"✅ Logged in as: {bot.user}")
    print("🚀 System is error-protected and online.")

if __name__ == "__main__":
    if TOKEN:
        Thread(target=run_web, daemon=True).start()
        bot.run(TOKEN)
    else:
        print("❌ ERROR: DISCORD_TOKEN is missing in .env")
