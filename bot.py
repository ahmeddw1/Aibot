import discord
from discord.ext import commands
from discord import app_commands, Embed, Interaction
import os
import asyncio
import logging
import yt_dlp
import g4f
from flask import Flask

# 1. TOTAL SILENCE (Removes IP/Flask logs)
logging.getLogger('werkzeug').disabled = True
os.environ['WERKZEUG_RUN_MAIN'] = 'true'

app = Flask('')

@app.route('/')
def home():
    return "Status: Online"

# 2. BOT CORE
TOKEN = os.environ.get("DISCORD_TOKEN")

class CodeWeaver(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # This syncs your /chat, /play, and /clear commands
        await self.tree.sync()
        print("💎 VIP System: Commands Synced.")

bot = CodeWeaver()

# --- COMMANDS ---
@bot.tree.command(name="chat", description="AI Coding Support")
async def chat(itx: Interaction, message: str):
    await itx.response.defer()
    try:
        response = await asyncio.to_thread(g4f.ChatCompletion.create, 
            model=g4f.models.gpt_4, 
            messages=[{"role": "user", "content": message}])
        await itx.followup.send(f"💻 **AI:**\n{str(response)[:1900]}")
    except:
        await itx.followup.send("⚠️ AI Busy.")

@bot.tree.command(name="play", description="Play Music")
async def play(itx: Interaction, query: str):
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

@bot.tree.command(name="clear", description="Clear messages")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(itx: Interaction, amount: int):
    await itx.channel.purge(limit=amount)
    await itx.response.send_message(f"🧹 Cleared {amount} messages.", ephemeral=True)

# 3. THE RAILWAY FIX (NON-BLOCKING STARTUP)
async def run_bot():
    await bot.start(TOKEN)

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

async def main():
    # Start Flask in the background
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, run_flask)
    # Start Bot in the foreground
    print("🚀 Launching Code Weaver V11...")
    await run_bot()

if __name__ == "__main__":
    if not TOKEN:
        print("❌ ERROR: Set DISCORD_TOKEN in Railway Variables!")
    else:
        asyncio.run(main())
