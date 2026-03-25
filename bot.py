import discord
from discord.ext import commands
from discord import app_commands, Embed, Interaction, ButtonStyle
import os
import asyncio
import threading
import logging
import yt_dlp
import g4f
from flask import Flask

# --- SILENCE INTERNAL LOGS ---
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
os.environ['WERKZEUG_RUN_MAIN'] = 'true'

# --- KEEP-ALIVE WEB SERVER ---
app = Flask('')

@app.route('/')
def home():
    return "Code Weaver V11: System Online"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

# --- BOT CONFIGURATION ---
TOKEN = os.environ.get("DISCORD_TOKEN")
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch',
    'nocheckcertificate': True,
    'source_address': '0.0.0.0'
}
FFMPEG_OPTS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

class CodeWeaver(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = CodeWeaver()

# --- AI CODING COMMAND ---
@bot.tree.command(name="chat", description="Premium AI Coding Support")
async def chat(itx: Interaction, message: str):
    await itx.response.defer()
    try:
        response = await asyncio.to_thread(g4f.ChatCompletion.create, 
            model=g4f.models.gpt_4, 
            messages=[{"role": "system", "content": "You are a senior developer."}, {"role": "user", "content": message}])
        await itx.followup.send(f"💻 **AI Assistant:**\n{str(response)[:1900]}")
    except:
        await itx.followup.send("⚠️ AI Engine is currently busy.")

# --- MUSIC COMMAND ---
@bot.tree.command(name="play", description="Stream Music from YouTube")
async def play(itx: Interaction, query: str):
    await itx.response.defer()
    if not itx.user.voice:
        return await itx.followup.send("❌ Please join a voice channel first.")
    
    vc = itx.guild.voice_client or await itx.user.voice.channel.connect()
    
    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(query, download=False)
            if 'entries' in info: info = info['entries'][0]
            url, title = info['url'], info['title']

        if vc.is_playing(): vc.stop()
        vc.play(discord.FFmpegPCMAudio(url, **FFMPEG_OPTS))
        await itx.followup.send(f"🎶 **Now Playing:** {title}")
    except Exception as e:
        await itx.followup.send(f"⚠️ Music Error: {str(e)}")

# --- UTILITY COMMAND ---
@bot.tree.command(name="clear", description="Clear channel messages")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(itx: Interaction, amount: int):
    await itx.response.defer(ephemeral=True)
    deleted = await itx.channel.purge(limit=amount)
    await itx.followup.send(f"✅ Deleted {len(deleted)} messages.")

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is connected and ready.")

# --- EXECUTION ---
if __name__ == "__main__":
    if TOKEN:
        threading.Thread(target=run_web, daemon=True).start()
        print("💎 Launching Code Weaver V11 Platinum...")
        bot.run(TOKEN)
    else:
        print("❌ CRITICAL ERROR: DISCORD_TOKEN is not set in Railway Variables.")
