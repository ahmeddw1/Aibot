import discord
from discord.ext import commands
import os
import asyncio
import logging
from flask import Flask
from threading import Thread
from waitress import serve  # Production Server

# 1. TOTAL SILENCE - Disable all web logging
logging.getLogger('waitress').setLevel(logging.ERROR)
logging.getLogger('werkzeug').setLevel(logging.ERROR)

app = Flask(__name__)

@app.route('/')
def health():
    return "VIP System Active", 200

# 2. BOT ENGINE
TOKEN = os.environ.get("DISCORD_TOKEN")

class CodeWeaver(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = CodeWeaver()

# --- CHAT & MUSIC COMMANDS ---
@bot.tree.command(name="chat", description="AI Coding Support")
async def chat(itx: discord.Interaction, message: str):
    await itx.response.defer()
    import g4f
    res = await asyncio.to_thread(g4f.ChatCompletion.create, model=g4f.models.gpt_4, messages=[{"role":"user","content":message}])
    await itx.followup.send(f"💻 **AI:** {str(res)[:1900]}")

@bot.tree.command(name="play", description="Play Music")
async def play(itx: discord.Interaction, query: str):
    await itx.response.defer()
    import yt_dlp
    if not itx.user.voice: return await itx.followup.send("Join VC!")
    vc = itx.guild.voice_client or await itx.user.voice.channel.connect()
    with yt_dlp.YoutubeDL({'format':'bestaudio','quiet':True}) as ydl:
        info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
    if vc.is_playing(): vc.stop()
    vc.play(discord.FFmpegPCMAudio(info['url'], before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5", options="-vn"))
    await itx.followup.send(f"🎶 Playing: **{info['title']}**")

# 3. PRODUCTION STARTUP (No Warnings, No IPs)
def run_production_server():
    port = int(os.environ.get("PORT", 8080))
    # 'serve' from waitress is the production way to do this
    serve(app, host='0.0.0.0', port=port, _quiet=True)

if __name__ == "__main__":
    if not TOKEN:
        print("❌ ERROR: Missing DISCORD_TOKEN")
    else:
        # Start production server silently in background
        Thread(target=run_production_server, daemon=True).start()
        
        print("💎 Code Weaver V11: System Online.")
        bot.run(TOKEN)
