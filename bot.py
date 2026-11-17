import asyncio, datetime, os, random, time, aiohttp
from aiohttp import web
import discord
from discord.ext import commands

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip().strip('"').strip("'")
STAFF_ROLE_IDS = [1567026563369664590]
HQ_CHANNEL_ID = 1568991830245253263
START_TIME, BOT_STATUS = time.time(), "Starting..."

def is_detective(m: discord.Member) -> bool:
    return isinstance(m, discord.Member) and (m.guild_permissions.administrator or any(r.id in STAFF_ROLE_IDS for r in m.roles))

async def run_web():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text=f"Detective Bureau Bot 24/7 | Up: {int((time.time()-START_TIME)//60)}m | Status: {BOT_STATUS}"))
    runner = web.AppRunner(app); await runner.setup()
    try: await web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 10000))).start()
    except Exception: pass

async def pinger():
    await asyncio.sleep(20)
    url = os.environ.get("RENDER_EXTERNAL_URL") or f"http://127.0.0.1:{os.environ.get('PORT', 10000)}/"
    async with aiohttp.ClientSession() as s:
        while True:
            try: await s.get(url, timeout=10)
            except Exception: pass
            await asyncio.sleep(240)

class EvidenceModal(discord.ui.Modal, title="🔬 Log Forensic / Crime Scene Evidence"):
    ev_type = discord.ui.TextInput(label="Evidence Type (e.g. Ballistics, CCTV, DNA)", placeholder="Shell casings / Witness statement / Screenshot", required=True, max_length=80)
    ev_desc = discord.ui.TextInput(label="Evidence Details & Screenshot Links", style=discord.TextStyle.paragraph, required=True, max_length=400)

    async def on_submit(self, i: discord.Interaction):
        emb = i.message.embeds[0]
        now = datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M UTC")
        old_ev = emb.fields[1].value if len(emb.fields) > 1 else ""
        if old_ev.startswith("*No forensic"): old_ev = ""
        new_entry = f"• `[{now}]` **{self.ev_type.value}** ({i.user.mention}): {self.ev_desc.value}"
        updated = (old_ev + "\n" + new_entry).strip()[:1020]
        emb.set_field_at(1, name="🔬 Logged Crime Scene Evidence", value=updated, inline=False)
        await i.response.edit_message(embed=emb, view=CaseFileView())

class CaseFileView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)

    @discord.ui.button(label="Log Evidence", style=discord.ButtonStyle.primary, emoji="🔬", custom_id="db:ev", row=0)
    async def ev_b(self, i: discord.Interaction, b: discord.ui.Button):
        await i.response.send_modal(EvidenceModal())

    @discord.ui.button(label="Request Warrant / Send to DOJ", style=discord.ButtonStyle.danger, emoji="🚨", custom_id="db:war", row=0)
    async def war_b(self, i: discord.Interaction, b: discord.ui.Button):
        if not is_detective(i.user): return await i.response.send_message("❌ Detectives / Staff only.", ephemeral=True)
        emb = i.message.embeds[0]; emb.color = discord.Color.red()
        emb.set_field_at(2, name="📌 Case Status", value=f"🚨 **WARRANT REQUESTED / SENT TO DOJ** by Det. {i.user.mention}", inline=False)
        await i.response.edit_message(embed=emb, view=self)
        hq = i.guild.get_channel(HQ_CHANNEL_ID) or i.channel
        await hq.send(content="@here 🚨 **Detective Bureau Arrest Warrant Filing!**", embed=emb)

    @discord.ui.button(label="Close Case (Solved)", style=discord.ButtonStyle.success, emoji="✅", custom_id="db:cls", row=0)
    async def cls_b(self, i: discord.Interaction, b: discord.ui.Button):
        if not is_detective(i.user): return await i.response.send_message("❌ Detectives / Staff only.", ephemeral=True)
        emb = i.message.embeds[0]; emb.color = discord.Color.green()
        emb.set_field_at(2, name="📌 Case Status", value=f"✅ **CASE SOLVED & CLOSED** by Det. {i.user.mention}", inline=False)
        for c in self.children: c.disabled = True
        await i.response.edit_message(embed=emb, view=self)

class NewCaseModal(discord.ui.Modal, title="🕵️ Open New Detective Case File"):
    suspect = discord.ui.TextInput(label="Primary Suspect(s) / Unknown", placeholder="Username or 'Unknown Masked Suspect'", required=True, max_length=100)
    crime = discord.ui.TextInput(label="Offense / Crime Investigated", placeholder="e.g. Armed Bank Robbery, Homicide, Grand Theft", required=True, max_length=120)
    summary = discord.ui.TextInput(label="Initial Crime Scene Report & Location", style=discord.TextStyle.paragraph, required=True, max_length=500)

    async def on_submit(self, i: discord.Interaction):
        cid = f"DB-{random.randint(1000, 9999)}"
        emb = discord.Embed(title=f"📁 DETECTIVE CASE FILE #{cid}", description=f"📍 **Crime Scene Summary:**\n> {self.summary.value}", color=discord.Color.from_rgb(47, 49, 54))
        emb.add_field(name="🕵️ Case Info", value=f"**Lead Detective:** {i.user.mention}\n**Suspect(s):** `{self.suspect.value}`\n**Offense:** `{self.crime.value}`", inline=False)
        emb.add_field(name="🔬 Logged Crime Scene Evidence", value="*No forensic evidence logged yet. Click **🔬 Log Evidence** below.*", inline=False)
        emb.add_field(name="📌 Case Status", value="🟡 **ACTIVE INVESTIGATION**", inline=False)
        await i.response.send_message(embed=emb, view=CaseFileView())

class BureauPanelView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Open New Detective Case File", style=discord.ButtonStyle.secondary, emoji="🕵️", custom_id="db:open")
    async def open_b(self, i: discord.Interaction, b: discord.ui.Button):
        await i.response.send_modal(NewCaseModal())

class DetectiveBot(commands.Bot):
    def __init__(self, msg_intent: bool = True):
        intents = discord.Intents.default(); intents.message_content = msg_intent
        super().__init__(command_prefix="!", intents=intents, help_command=None)
    async def setup_hook(self):
        self.add_view(CaseFileView()); self.add_view(BureauPanelView()); await self.tree.sync()
    async def on_ready(self):
        global BOT_STATUS; BOT_STATUS = f"ONLINE as {self.user}"
        print(f"✅ Detective Bureau Bot ONLINE as {self.user}")

def reg_cmds(b: DetectiveBot):
    @b.tree.command(name="detective_panel", description="Post the Detective Bureau Case File & Evidence Center")
    async def s_dp(i: discord.Interaction):
        if not is_detective(i.user): return await i.response.send_message("❌ Staff only.", ephemeral=True)
        emb = discord.Embed(title="🕵️ Police Detective Bureau — Investigations Division", description="Click below to open an official **📁 Detective Case File**, log crime scene forensics, and submit cases for **SWAT Warrants** or **DOJ Trials**.", color=discord.Color.from_rgb(47, 49, 54))
        await i.response.send_message(embed=emb, view=BureauPanelView())

    @b.tree.command(name="open_case", description="Directly open a numbered Detective Case File")
    async def s_oc(i: discord.Interaction, suspect: str, crime: str, crime_scene_notes: str):
        cid = f"DB-{random.randint(1000, 9999)}"
        emb = discord.Embed(title=f"📁 DETECTIVE CASE FILE #{cid}", description=f"📍 **Crime Scene Summary:**\n> {crime_scene_notes}", color=discord.Color.from_rgb(47, 49, 54))
        emb.add_field(name="🕵️ Case Info", value=f"**Lead Detective:** {i.user.mention}\n**Suspect(s):** `{suspect}`\n**Offense:** `{crime}`", inline=False)
        emb.add_field(name="🔬 Logged Crime Scene Evidence", value="*No forensic evidence logged yet. Click **🔬 Log Evidence** below.*", inline=False)
        emb.add_field(name="📌 Case Status", value="🟡 **ACTIVE INVESTIGATION**", inline=False)
        await i.response.send_message(embed=emb, view=CaseFileView())

async def main():
    global BOT_STATUS
    await run_web(); asyncio.create_task(pinger())
    if not BOT_TOKEN:
        BOT_STATUS = "MISSING BOT_TOKEN IN RENDER ENVIRONMENT"
        while True: await asyncio.sleep(3600)
    bot = DetectiveBot(True); reg_cmds(bot)
    try: await bot.start(BOT_TOKEN)
    except discord.PrivilegedIntentsRequired:
        await bot.close(); bot = DetectiveBot(False); reg_cmds(bot); await bot.start(BOT_TOKEN)
    except Exception as e:
        BOT_STATUS = f"ERROR: {type(e).__name__}: {e}"
        while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
