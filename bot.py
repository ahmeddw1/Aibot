import discord
from discord.ext import commands
import os
import asyncio
import logging
import yt_dlp
import g4f
from flask import Flask
from threading import Thread

# 1. COMPLETELY SILENCE ALL WEB LOGS
# This removes the "WARNING", "Running on all addresses", and "IP" lines
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
os.environ['WERKZEUG_RUN_MAIN'] = 'true'

app = Flask(__name__)

@app.route('/')
def health_check():
    return "OK", 200

# 2. BOT CORE
TOKEN = os.environ.get("DISCORD_TOKEN")

class CodeWeaver(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("💎 VIP System: Slash Commands Synced.")

bot = CodeWeaver()

# --- AI COMMAND ---
@bot.tree.command(name="chat", description="AI Coding Support")
async def chat(itx: discord.Interaction, message: str):
    await itx.response.defer()
    try:
        response = await asyncio.to_thread(g4f.ChatCompletion.create, 
            model=g4f.models.gpt_4, 
            messages=[{"role": "user", "content": message}])
        await itx.followup.send(f"💻 **AI:**\n{str(response)[:1900]}")
    except:
        await itx.followup.send("⚠️ AI Engine Busy.")

# --- MUSIC COMMAND ---
@bot.tree.command(name="play", description="Play Music")
async def play(itx: discord.Interaction, query: str):
    await itx.response.defer()
    if not itx.user.voice: return await itx.followup.send("Join VC first!")
    vc = itx.guild.voice_client or await itx.user.voice.channel.connect()
    
    ydl_opts = {'format': 'bestaudio/best', 'noplaylist': True, 'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
        url = info['url']
    
    if vc.is_playing(): vc.stop()
    vc.play(discord.FFmpegPCMAudio(url, before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5", options="-vn"))
    await itx.followup.send(f"🎶 Playing: **{info['title']}**")

# --- CLEAR COMMAND ---
@bot.tree.command(name="clear", description="Clear messages")
async def clear(itx: discord.Interaction, amount: int):
    if itx.user.guild_permissions.manage_messages:
        await itx.channel.purge(limit=amount)
        await itx.response.send_message(f"🧹 Cleared {amount} messages.", ephemeral=True)
    else:
        await itx.response.send_message("❌ No Permission.", ephemeral=True)

# 3. THE ULTIMATE STARTUP FIX
def start_server():
    # Railway passes the PORT env; we use it and stay silent
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    if not TOKEN:
        print("❌ CRITICAL: DISCORD_TOKEN is missing in Railway Variables!")
    else:
        # Start the web server in a separate background thread
        # This keeps Railway happy without blocking the bot
        Thread(target=start_server, daemon=True).start()
        
        print("🚀 Code Weaver V11: Booting Discord Core...")
        # Start the bot in the main thread
        bot.run(TOKEN)
