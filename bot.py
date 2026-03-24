import discord
from discord.ext import commands
from discord import app_commands, Embed, Interaction, ButtonStyle
import os
import asyncio
import yt_dlp
import g4f
from flask import Flask
from threading import Thread

# --- RAILWAY WEB SERVER (Keep-Alive) ---
app = Flask('')

@app.route('/')
def home():
    return "Code Weaver V11 is Online"

def run_web():
    # Railway provides a PORT environment variable
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- BOT CONFIGURATION ---
TOKEN = os.environ.get("DISCORD_TOKEN")
# On Railway, ffmpeg is usually in the system PATH
FFMPEG_PATH = "ffmpeg" 

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch',
    'nocheckcertificate': True,
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
        self.loop_states = {}

    async def setup_hook(self):
        await self.tree.sync()
        print("💎 V11 Platinum: Commands Synced")

bot = CodeWeaver()

# --- MUSIC COMMANDS ---
@bot.tree.command(name="play", description="VIP Music Stream")
async def play(itx: Interaction, query: str):
    await itx.response.defer()
    if not itx.user.voice:
        return await itx.followup.send("Join a Voice Channel first!")
    
    vc = itx.guild.voice_client or await itx.user.voice.channel.connect()
    
    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        info = ydl.extract_info(query, download=False)
        if 'entries' in info: info = info['entries'][0]
        url, title = info['url'], info['title']

    if vc.is_playing(): vc.stop()
    vc.play(discord.FFmpegPCMAudio(url, **FFMPEG_OPTS))
    await itx.followup.send(f"🎶 Playing: **{title}**")

@bot.tree.command(name="chat", description="AI Coding Support")
async def chat(itx: Interaction, chat: str):
    await itx.response.defer()
    res = await asyncio.to_thread(g4f.ChatCompletion.create, 
        model=g4f.models.gpt_4, 
        messages=[{"role": "user", "content": chat}])
    await itx.followup.send(f"💻 **AI:**\n{str(res)[:1950]}")

# --- STARTUP ---
if __name__ == "__main__":
    # Start Web Server in background for Railway
    Thread(target=run_web).start()
    
    # Start Bot
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ ERROR: DISCORD_TOKEN environment variable not found!")