import discord
from discord.ext import commands
from discord import app_commands, Interaction, File
import os
import io
import asyncio
import requests
import logging
from flask import Flask
from threading import Thread
from waitress import serve
import g4f

# --- SILENCE WEB LOGS ---
logging.getLogger('waitress').setLevel(logging.ERROR)
logging.getLogger('werkzeug').setLevel(logging.ERROR)

app = Flask(__name__)
@app.route('/')
def health(): return "Online", 200

TOKEN = os.environ.get("DISCORD_TOKEN")

class CodeWeaver(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = CodeWeaver()

# --- AI TEXT LOGIC ---
async def get_ai_response(content):
    try:
        res = await asyncio.to_thread(g4f.ChatCompletion.create, 
            model=g4f.models.gpt_4, 
            messages=[{"role": "user", "content": content}])
        return str(res)[:1950]
    except: return "⚠️ AI Text Engine busy."

# --- IMAGE GENERATION LOGIC ---
# This uses a poll of free providers to generate the actual image file
async def get_ai_image(prompt):
    try:
        # We use g4f's image provider or a stable fallback
        response = await asyncio.to_thread(g4f.ChatCompletion.create,
            model=g4f.models.gpt_4, # Some providers in g4f support image out
            messages=[{"role": "user", "content": prompt}],
            image=True) 
        return response # This usually returns a URL
    except:
        # Fallback to a direct Pollination/Stable Diffusion API if g4f image fails
        return f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}?width=1024&height=1024&nologo=true"

# --- COMMANDS ---
@bot.tree.command(name="chat", description="AI Chat")
async def chat(itx: Interaction, message: str):
    await itx.response.defer()
    await itx.followup.send(f"💻 **AI:** {await get_ai_response(message)}")

@bot.tree.command(name="image", description="Generate Image (Nano Banana Style)")
async def image(itx: Interaction, prompt: str):
    await itx.response.defer()
    img_url = await get_ai_image(prompt)
    
    # Download the image to send as a real file
    img_data = requests.get(img_url).content
    with io.BytesIO(img_data) as img_file:
        file = File(fp=img_file, filename="nano_banana.png")
        await itx.followup.send(content=f"🎨 **Prompt:** `{prompt}`", file=file)

@bot.tree.command(name="clear", description="Clear chat")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(itx: Interaction, amount: int):
    await itx.channel.purge(limit=amount)
    await itx.response.send_message(f"🧹 Done.", ephemeral=True)

# --- DM SUPPORT ---
@bot.event
async def on_message(msg):
    if msg.author == bot.user: return
    if isinstance(msg.channel, discord.DMChannel):
        async with msg.channel.typing():
            # Auto-detect if they want an image in DMs
            if "draw" in msg.content.lower() or "image" in msg.content.lower():
                url = await get_ai_image(msg.content)
                img_data = requests.get(url).content
                with io.BytesIO(img_data) as f:
                    await msg.author.send(file=File(f, "dm_art.png"))
            else:
                await msg.author.send(await get_ai_response(msg.content))

# --- PRODUCTION START ---
def run_web():
    serve(app, host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), _quiet=True)

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    bot.run(TOKEN)
