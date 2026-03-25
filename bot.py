import discord
from discord.ext import commands
from discord import app_commands, Interaction, File
import os, io, asyncio, logging, requests
import google.generativeai as genai
from flask import Flask
from threading import Thread
from waitress import serve

# --- 1. SILENT PRODUCTION SETUP ---
logging.getLogger('waitress').setLevel(logging.ERROR)
logging.getLogger('werkzeug').setLevel(logging.ERROR)
app = Flask(__name__)
@app.route('/')
def health(): return "Omni-System Online", 200

# --- 2. CONFIGURATION ---
TOKEN = os.environ.get("DISCORD_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_KEY)
chat_model = genai.GenerativeModel('gemini-1.5-flash')
img_model = genai.GenerativeModel('imagen-3.0-generate-001') # Ensure API access

class OmniBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self):
        await self.tree.sync()

bot = OmniBot()

# --- 3. CORE AI FUNCTIONS ---
async def get_text(prompt):
    try:
        response = await asyncio.to_thread(chat_model.generate_content, prompt)
        return response.text[:1900]
    except: return "⚠️ Chat engine busy."

async def get_image(prompt):
    try:
        response = await asyncio.to_thread(img_model.generate_content, prompt)
        if response.candidates[0].content.parts[0].inline_data:
            return io.BytesIO(response.candidates[0].content.parts[0].inline_data.data)
    except:
        # Fallback to high-speed public API if Gemini key lacks Imagen permission
        url = f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}?nologo=true"
        return io.BytesIO(requests.get(url).content)

# --- 4. SLASH COMMANDS (The "All-In-One" List) ---

@bot.tree.command(name="chat", description="Chat with Gemini AI")
async def chat_cmd(itx: Interaction, message: str):
    await itx.response.defer()
    await itx.followup.send(f"♊ **AI:** {await get_text(message)}")

@bot.tree.command(name="image", description="Generate high-quality AI art")
async def image_cmd(itx: Interaction, prompt: str):
    await itx.response.defer()
    buf = await get_image(prompt)
    await itx.followup.send(file=File(fp=buf, filename="art.png"))

@bot.tree.command(name="clear", description="Purge messages")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear_cmd(itx: Interaction, amount: int):
    await itx.channel.purge(limit=amount)
    await itx.response.send_message(f"🧹 Purged {amount} messages.", ephemeral=True)

@bot.tree.command(name="help", description="Show all commands")
async def help_cmd(itx: Interaction):
    embed = discord.Embed(title="Omni-Bot V11 | Commands", color=0x2ecc71)
    embed.add_field(name="/chat [msg]", value="Talk to Gemini Pro", inline=False)
    embed.add_field(name="/image [prompt]", value="Generate Imagen-3 Art", inline=False)
    embed.add_field(name="/clear [num]", value="Delete messages (Admin)", inline=False)
    embed.add_field(name="DM Mode", value="Send me a message or 'draw [prompt]' in DMs!", inline=False)
    await itx.response.send_message(embed=embed)

# --- 5. SMART DM & MESSAGE HANDLER ---
@bot.event
async def on_message(msg):
    if msg.author == bot.user: return

    # If it's a DM, handle automatically
    if isinstance(msg.channel, discord.DMChannel):
        async with msg.channel.typing():
            if any(k in msg.content.lower() for k in ["draw", "image", "art"]):
                buf = await get_image(msg.content)
                await msg.author.send(file=File(fp=buf, filename="dm_art.png"))
            else:
                await msg.author.send(await get_text(msg.content))
    
    await bot.process_commands(msg)

# --- 6. EXECUTION ---
def run_web(): serve(app, host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), _quiet=True)

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    if TOKEN:
        print("💎 Omni-Bot Online. All commands synced.")
        bot.run(TOKEN)
