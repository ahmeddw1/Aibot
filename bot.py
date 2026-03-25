import discord
from discord.ext import commands
from discord import app_commands, Interaction, File
import os
import io
import asyncio
import logging
import re
from google import genai
from flask import Flask
from threading import Thread
from waitress import serve

# --- 1. SILENT PRODUCTION SERVER ---
logging.getLogger('waitress').setLevel(logging.ERROR)
logging.getLogger('werkzeug').setLevel(logging.ERROR)

app = Flask(__name__)
@app.route('/')
def health(): return "Architect System: Online", 200

# --- 2. GENAI CLIENT ---
client = genai.Client()

class CodeWeaver(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self):
        await self.tree.sync()

bot = CodeWeaver()

# --- 3. HELPER: CODE TO FILE EXTRACTOR ---
def extract_code_to_files(text):
    """Detects code blocks and prepares Discord Files."""
    # Pattern to find ```language \n code ```
    regex = r"```(\w+)\n([\s\S]*?)```"
    matches = re.findall(regex, text)
    files = []
    
    extensions = {
        "python": "py", "py": "py",
        "javascript": "js", "js": "js", "node": "js",
        "java": "java",
        "html": "html",
        "css": "css",
        "typescript": "ts", "ts": "ts",
        "c++": "cpp", "cpp": "cpp",
        "csharp": "cs", "cs": "cs"
    }

    for i, (lang, code) in enumerate(matches):
        ext = extensions.get(lang.lower(), "txt")
        filename = f"script_{i+1}.{ext}"
        
        # Create a file-like object in memory
        stream = io.BytesIO(code.encode('utf-8'))
        files.append(File(fp=stream, filename=filename))
        
    return files

# --- 4. CORE AI LOGIC ---

async def handle_ai_request(msg_obj, prompt, is_dm=False):
    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-3-flash-preview",
            contents=prompt
        )
        full_text = response.text
        
        # Extract files if code exists
        code_files = extract_code_to_files(full_text)
        
        # Clean text: remove long code blocks from the message to keep it readable
        clean_text = re.sub(r"```[\s\S]*?```", "*(Code extracted to file below)*", full_text)
        
        if is_dm:
            await msg_obj.author.send(clean_text[:1900], files=code_files)
        else:
            await msg_obj.followup.send(clean_text[:1900], files=code_files)

    except Exception as e:
        err = f"⚠️ System Error: {str(e)}"
        if is_dm: await msg_obj.author.send(err)
        else: await msg_obj.followup.send(err)

# --- 5. COMMANDS ---

@bot.tree.command(name="chat", description="AI Coding Assistant (Generates Files)")
async def chat(itx: Interaction, message: str):
    await itx.response.defer()
    await handle_ai_request(itx, message)

@bot.tree.command(name="image", description="Generate high-end images")
async def image(itx: Interaction, prompt: str):
    await itx.response.defer()
    try:
        res = await asyncio.to_thread(client.models.generate_content, 
                                     model="gemini-3.1-flash-image-preview", contents=[prompt])
        for part in res.parts:
            if part.inline_data:
                img = part.as_image()
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                buf.seek(0)
                return await itx.followup.send(file=File(fp=buf, filename="gen.png"))
        await itx.followup.send("❌ No image data returned.")
    except Exception as e:
        await itx.followup.send(f"⚠️ Image Error: {e}")

# --- 6. SMART DM LISTENER ---

@bot.event
async def on_message(msg):
    if msg.author == bot.user: return

    if isinstance(msg.channel, discord.DMChannel):
        async with msg.channel.typing():
            content = msg.content.lower()
            # If user asks for an image
            if any(k in content for k in ["draw", "image", "art"]):
                # Image logic for DMs
                try:
                    res = await asyncio.to_thread(client.models.generate_content, 
                                                 model="gemini-3.1-flash-image-preview", contents=[msg.content])
                    for part in res.parts:
                        if part.inline_data:
                            img = part.as_image()
                            buf = io.BytesIO()
                            img.save(buf, format='PNG')
                            buf.seek(0)
                            return await msg.author.send(file=File(fp=buf, filename="dm_gen.png"))
                except: pass
            
            # Default: Chat + Code File Extraction
            await handle_ai_request(msg, msg.content, is_dm=True)

    await bot.process_commands(msg)

# --- 7. STARTUP ---

def run_web():
    serve(app, host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), _quiet=True)

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    bot.run(os.environ.get("DISCORD_TOKEN"))
