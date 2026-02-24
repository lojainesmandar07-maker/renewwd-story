import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import sqlite3
import random
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from flask import Flask
from threading import Thread

# ============================================
# إعدادات تسجيل الأخطاء (Logging)
# ============================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("game_log.txt", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================
# إعدادات الصلاحيات (Intents)
# ============================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

# ============================================
# خادم Flask للحفاظ على البوت نشطاً
# ============================================
app = Flask('')

@app.route('/')
def home():
    return "I am alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# ============================================
# محمل القصة (Story Loader)
# ============================================
class StoryLoader:
    """يتعامل مع ملف القصة JSON ويقوم بتحليل البيانات بشكل متقدم"""
    
    def __init__(self, story_file: str = "story.json"):
        self.story_file = story_file
        self.data = self.load_story()
    
    def load_story(self) -> Dict:
        try:
            if os.path.exists(self.story_file):
                with open(self.story_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"✅ تم تحميل القصة بنجاح: {data.get('metadata', {}).get('name')}")
                    return data
            else:
                logger.warning("⚠️ ملف القصة غير موجود، سيتم استخدام قصة افتراضية.")
                return self.create_default_story()
        except Exception as e:
            logger.critical(f"⚠️ خطأ في تحميل القصة: {e}")
            return self.create_default_story()
    
    def create_default_story(self) -> Dict:
        return {
            "metadata": {
                "name": "رحلة الشظايا",
                "version": "3.0",
                "variables": ["shards", "corruption", "mystery", "reputation", "alignment", "trust_aren", "world_stability", "xp", "level"],
                "achievements": ["first_choice"]
            },
            "parts": {
                "PART_01": {
                    "id": "PART_01",
                    "title": "⚡ الاكتشاف",
                    "text": "أنقاض موقع طاقة غامض...",
                    "image": "",
                    "choices": [
                        {"text": "💎 لمس الشظية فورًا", "emoji": "💎", "next": "PART_02", "effects": {"shards": 1, "corruption": 5, "mystery": 3, "achievement": "first_choice"}},
                        {"text": "🔍 تحليلها أولًا", "emoji": "🔍", "next": "PART_02", "effects": {"shards": 1, "corruption": 2, "reputation": 1, "achievement": "first_choice"}}
                    ]
                },
                "PART_02": {
                    "id": "PART_02",
                    "title": "العبور الأول",
                    "text": "تمد يدك...",
                    "image": "",
                    "choices": [
                        {"text": "🛡️ تقف", "emoji": "🛡️", "next": "PART_03", "effects": {"alignment": "Gray"}}
                    ]
                }
            },
            "achievements_data": {
                "first_choice": {"name": "أول قرار", "description": "اتخذت أول قرار", "emoji": "🎯"}
            }
        }
    
    def get_part(self, part_id: str) -> Optional[Dict]:
        part = self.data.get("parts", {}).get(part_id)
        if part:
            part['id'] = part_id
        return part
    
    def get_achievement_info(self, achievement_id: str) -> Dict:
        return self.data.get("achievements_data", {}).get(
            achievement_id,
            {"name": achievement_id, "description": "إنجاز غامض", "emoji": "🏆"}
        )
    
    def get_metadata(self) -> Dict:
        return self.data.get("metadata", {})

# ============================================
# قاعدة البيانات المتكاملة (Database)
# ============================================
class Database:
    def __init__(self, db_file: str = "shard_game.db"):
        self.db_file = db_file
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            current_part TEXT DEFAULT 'PART_01',
            shards INTEGER DEFAULT 0,
            corruption INTEGER DEFAULT 0,
            mystery INTEGER DEFAULT 0,
            reputation INTEGER DEFAULT 0,
            alignment TEXT DEFAULT 'Gray',
            trust_aren INTEGER DEFAULT 0,
            world_stability INTEGER DEFAULT 100,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            location TEXT DEFAULT 'أنقاض',
            last_daily TEXT,
            last_updated TEXT
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS achievements (
            user_id INTEGER,
            achievement_id TEXT,
            unlocked_at TEXT,
            PRIMARY KEY (user_id, achievement_id)
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER,
            item_id TEXT,
            item_name TEXT,
            quantity INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, item_id)
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS flags (
            user_id INTEGER,
            flag_name TEXT,
            flag_value INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, flag_name)
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            part_id TEXT,
            choice_text TEXT,
            impact_summary TEXT,
            timestamp TEXT
        )''')
        
        conn.commit()
        conn.close()
    
    def get_player(self, user_id: int) -> Optional[Dict]:
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        conn.close()
        if row:
            return dict(row)
        return None
    
    def create_player(self, user_id: int):
        now = datetime.now().isoformat()
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute('''INSERT OR IGNORE INTO players 
                     (user_id, current_part, shards, corruption, mystery, reputation, alignment, trust_aren, world_stability, xp, level, location, last_daily, last_updated)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (user_id, 'PART_01', 0, 0, 0, 0, 'Gray', 0, 100, 0, 1, 'أنقاض', None, now))
        conn.commit()
        self.add_to_inventory(user_id, "potion", "🧪 جرعة نقاء", 3)
        conn.close()
    
    def update_player(self, user_id: int, updates: Dict):
        if not updates:
            return
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        params = list(updates.values())
        params.append(datetime.now().isoformat())
        params.append(user_id)
        c.execute(f"UPDATE players SET {set_clause}, last_updated = ? WHERE user_id = ?", tuple(params))
        conn.commit()
        conn.close()
    
    def unlock_achievement(self, user_id: int, achievement_id: str) -> bool:
        try:
            conn = sqlite3.connect(self.db_file)
            c = conn.cursor()
            c.execute("INSERT INTO achievements (user_id, achievement_id, unlocked_at) VALUES (?, ?, ?)",
                      (user_id, achievement_id, datetime.now().isoformat()))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def get_achievements(self, user_id: int) -> List[Dict]:
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM achievements WHERE user_id = ?", (user_id,))
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    
    def set_flag(self, user_id: int, flag_name: str, value: int = 1):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute('''INSERT INTO flags (user_id, flag_name, flag_value)
                     VALUES (?, ?, ?)
                     ON CONFLICT(user_id, flag_name) DO UPDATE SET flag_value = excluded.flag_value''',
                  (user_id, flag_name, value))
        conn.commit()
        conn.close()
    
    def get_flag(self, user_id: int, flag_name: str) -> int:
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("SELECT flag_value FROM flags WHERE user_id = ? AND flag_name = ?", (user_id, flag_name))
        result = c.fetchone()
        conn.close()
        return result[0] if result else 0
    
    def add_to_inventory(self, user_id: int, item_id: str, item_name: str = None, quantity: int = 1):
        if not item_name:
            item_name = item_id
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute('''INSERT INTO inventory (user_id, item_id, item_name, quantity)
                     VALUES (?, ?, ?, ?)
                     ON CONFLICT(user_id, item_id) DO UPDATE SET
                     quantity = quantity + excluded.quantity,
                     item_name = excluded.item_name''',
                  (user_id, item_id, item_name, quantity))
        conn.commit()
        conn.close()
    
    def remove_from_inventory(self, user_id: int, item_id: str, quantity: int = 1):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute('''UPDATE inventory SET quantity = quantity - ?
                     WHERE user_id = ? AND item_id = ?''', (quantity, user_id, item_id))
        c.execute('''DELETE FROM inventory WHERE user_id = ? AND item_id = ? AND quantity <= 0''', (user_id, item_id))
        conn.commit()
        conn.close()
    
    def get_inventory(self, user_id: int) -> List[Dict]:
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT item_id, item_name, quantity FROM inventory WHERE user_id = ? AND quantity > 0", (user_id,))
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    
    def has_item(self, user_id: int, item_id: str, quantity: int = 1) -> bool:
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?", (user_id, item_id))
        result = c.fetchone()
        conn.close()
        return result is not None and result[0] >= quantity
    
    def add_history(self, user_id: int, part_id: str, choice_text: str, impact: str):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("INSERT INTO history (user_id, part_id, choice_text, impact_summary, timestamp) VALUES (?, ?, ?, ?, ?)",
                  (user_id, part_id, choice_text, impact, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    
    def get_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM history WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

# ============================================
# واجهات مساعدة (UI Helpers)
# ============================================
class GameUI:
    @staticmethod
    def create_progress_bar(current: int, maximum: int, length: int = 12) -> str:
        percent = max(0, min(current / maximum, 1.0))
        filled = int(length * percent)
        bar = "🟦" * filled + "⬜" * (length - filled)
        return f"{bar} ({current}/{maximum})"
    
    @staticmethod
    def clamp(value: int, min_val: int, max_val: int) -> int:
        return max(min_val, min(max_val, value))
    
    @staticmethod
    def get_alignment_emoji(alignment: str) -> str:
        return {"Light": "✨", "Gray": "⚪", "Dark": "🌑"}.get(alignment, "⚪")

# ============================================
# عرض القصة مع الأزرار (محدث مع تسجيل)
# ============================================
class StoryView(discord.ui.View):
    def __init__(self, bot, user_id: int, part_data: Dict):
        super().__init__(timeout=None)
        self.bot = bot
        self.user_id = user_id
        self.part_data = part_data
        self._setup_buttons()
    
    def _setup_buttons(self):
        for i, choice in enumerate(self.part_data.get("choices", [])):
            style = discord.ButtonStyle.primary
            if "⚔️" in choice.get("emoji", "") or "قتال" in choice.get("text", ""):
                style = discord.ButtonStyle.danger
            elif "هرب" in choice.get("text", ""):
                style = discord.ButtonStyle.secondary
            
            # إنشاء custom_id ثابت نسبياً
            custom_id = f"c_{self.part_data['id']}_{i}_{self.user_id}"
            
            btn = discord.ui.Button(
                label=choice.get("text", f"خيار {i+1}")[:80],
                custom_id=custom_id,
                emoji=choice.get("emoji"),
                style=style
            )
            btn.callback = self._create_callback(choice)
            self.add_item(btn)
    
    def _create_callback(self, choice):
        async def callback(interaction: discord.Interaction):
            # تسجيل الضغط على الزر
            logger.info(f"User {interaction.user.id} clicked button: {choice.get('text')}")
            try:
                if interaction.user.id != self.user_id:
                    await interaction.response.send_message("❌ هذه القصة ليست لك!", ephemeral=True)
                    return
                
                await interaction.response.defer()
                
                player = self.bot.db.get_player(self.user_id)
                if not player:
                    self.bot.db.create_player(self.user_id)
                    player = self.bot.db.get_player(self.user_id)
                
                # فحص الشروط
                requirements = choice.get("require", {})
                for var, min_val in requirements.items():
                    if var == "flag":
                        if self.bot.db.get_flag(self.user_id, min_val) == 0:
                            await interaction.followup.send(f"⚠️ لا يمكنك اختيار هذا المسار بعد.", ephemeral=True)
                            return
                    else:
                        if player.get(var, 0) < min_val:
                            await interaction.followup.send(
                                f"⚠️ **متطلب ناقص!** تحتاج إلى `{min_val}` من نقاط `{var}` لاختيار هذا المسار.",
                                ephemeral=True
                            )
                            return
                
                # نظام الاحتمالات
                success = random.randint(1, 100) <= choice.get("chance", 100)
                next_id = choice.get("next") if success else choice.get("fail_next", choice.get("next"))
                effects = choice.get("effects" if success else "fail_effects", {})
                
                updates = {"current_part": next_id}
                impact_log = []
                
                for var, val in effects.items():
                    if var == "achievement":
                        if self.bot.db.unlock_achievement(self.user_id, val):
                            ach = self.bot.story_loader.get_achievement_info(val)
                            await interaction.followup.send(f"🏆 **إنجاز جديد:** {ach['emoji']} {ach['name']}", ephemeral=True)
                        continue
                    
                    if var == "inventory_add":
                        if isinstance(val, dict):
                            item_id = val.get("id", "unknown")
                            item_name = val.get("name", item_id)
                            qty = val.get("qty", 1)
                            self.bot.db.add_to_inventory(self.user_id, item_id, item_name, qty)
                            impact_log.append(f"حصلت على {item_name} x{qty}")
                        else:
                            self.bot.db.add_to_inventory(self.user_id, val, val)
                            impact_log.append(f"حصلت على {val}")
                        continue
                    
                    if var == "inventory_remove":
                        if isinstance(val, dict):
                            item_id = val.get("id")
                            qty = val.get("qty", 1)
                            self.bot.db.remove_from_inventory(self.user_id, item_id, qty)
                            impact_log.append(f"فقدت {item_id} x{qty}")
                        else:
                            self.bot.db.remove_from_inventory(self.user_id, val)
                            impact_log.append(f"فقدت {val}")
                        continue
                    
                    if var == "flag":
                        self.bot.db.set_flag(self.user_id, val, 1)
                        impact_log.append(f"علم: {val}")
                        continue
                    
                    if var == "relationship":
                        if ':' in val:
                            char, change = val.split(':', 1)
                            try:
                                change = int(change)
                                self.bot.db.set_flag(self.user_id, f"rel_{char}", change)
                                impact_log.append(f"علاقة {char}: {change:+}")
                            except:
                                pass
                        continue
                    
                    if var in ["alignment", "dragon_alliance", "rival_status"]:
                        updates[var] = val
                        impact_log.append(f"{var} = {val}")
                    else:
                        current = player.get(var, 0)
                        new_val = current + val
                        if var == "corruption":
                            new_val = GameUI.clamp(new_val, 0, 100)
                        elif var == "mystery":
                            new_val = GameUI.clamp(new_val, 0, 100)
                        elif var == "world_stability":
                            new_val = GameUI.clamp(new_val, 0, 100)
                        elif var == "reputation":
                            new_val = GameUI.clamp(new_val, -50, 50)
                        elif var == "trust_aren":
                            new_val = GameUI.clamp(new_val, 0, 100)
                        elif var == "shards":
                            new_val = max(0, new_val)
                        else:
                            new_val = max(0, new_val)
                        updates[var] = new_val
                        impact_log.append(f"{var}: {val:+}")
                
                xp_gain = random.randint(10, 20)
                updates["xp"] = player.get("xp", 0) + xp_gain
                impact_log.append(f"XP: +{xp_gain}")
                
                if updates["xp"] >= 100:
                    updates["xp"] = updates["xp"] - 100
                    updates["level"] = player.get("level", 1) + 1
                    impact_log.append(f"⬆️ مستوى {updates['level']}!")
                
                self.bot.db.update_player(self.user_id, updates)
                impact_summary = ", ".join(impact_log) if impact_log else "لا تأثير"
                self.bot.db.add_history(self.user_id, self.part_data['id'], choice.get('text', ''), impact_summary)
                
                next_part = self.bot.story_loader.get_part(next_id)
                if next_part:
                    updated_player = self.bot.db.get_player(self.user_id)
                    embed = self.bot.create_game_embed(next_part, updated_player)
                    await interaction.edit_original_response(
                        content="✅ تم تنفيذ قرارك!" if success else "⚠️ فشلت المحاولة وتغير المسار!",
                        embed=embed,
                        view=StoryView(self.bot, self.user_id, next_part)
                    )
                else:
                    await interaction.edit_original_response(
                        content="🏁 شكراً لك على إنهاء الرحلة!",
                        embed=None,
                        view=None
                    )
            except Exception as e:
                logger.error(f"خطأ في callback: {e}", exc_info=True)
                await interaction.followup.send(f"❌ حدث خطأ غير متوقع: {str(e)}", ephemeral=True)
        
        return callback

# ============================================
# البوت الرئيسي
# ============================================
class ShardBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.story_loader = StoryLoader()
        self.db = Database()
    
    async def setup_hook(self):
        await self.tree.sync()
        logger.info("✅ تم مزامنة الأوامر")
    
    def create_game_embed(self, part: Dict, p: Dict) -> discord.Embed:
        alignment_color = {
            "Light": discord.Color.gold(),
            "Gray": discord.Color.light_grey(),
            "Dark": discord.Color.dark_purple()
        }.get(p.get('alignment', 'Gray'), discord.Color.purple())
        
        embed = discord.Embed(
            title=f"📖 {part.get('title', 'فصل جديد')}",
            description=part.get('text', '')[:4000],
            color=alignment_color,
            timestamp=datetime.now()
        )
        
        if part.get("image"):
            embed.set_image(url=part["image"])
        
        stats = (
            f"💎 **الشظايا:** {p.get('shards', 0)}\n"
            f"🌑 **الفساد:** {GameUI.create_progress_bar(p.get('corruption', 0), 100)}\n"
            f"🔮 **الغموض:** {GameUI.create_progress_bar(p.get('mystery', 0), 100)}\n"
            f"⭐ **السمعة:** {p.get('reputation', 0)} ({p.get('reputation', 0)/50*100:.0f}%)\n"
            f"{GameUI.get_alignment_emoji(p.get('alignment', 'Gray'))} **التوجه:** {p.get('alignment', 'Gray')}\n"
            f"🤝 **ثقة أرين:** {p.get('trust_aren', 0)}%\n"
            f"🌍 **استقرار العالم:** {GameUI.create_progress_bar(p.get('world_stability', 100), 100)}\n"
            f"🌟 **المستوى:** {p.get('level', 1)} ({p.get('xp', 0)}/100 XP)"
        )
        embed.add_field(name="🛡️ حالة المغامر", value=stats, inline=False)
        embed.set_footer(text=f"معرف الجزء: {part['id']} • رحلة الشظايا")
        return embed

bot = ShardBot()

# ============================================
# أوامر الس slash
# ============================================
@bot.tree.command(name="ابدأ", description="🚀 ابدأ رحلة الشظايا")
async def start(interaction: discord.Interaction):
    user_id = interaction.user.id
    player = bot.db.get_player(user_id)
    
    if player and player.get('current_part') != 'PART_01':
        view = discord.ui.View()
        continue_btn = discord.ui.Button(label="⏩ استمر", style=discord.ButtonStyle.primary)
        reset_btn = discord.ui.Button(label="🔄 ابدأ من جديد", style=discord.ButtonStyle.danger)
        
        async def continue_callback(interaction: discord.Interaction):
            await continue_game(interaction)
        
        async def reset_callback(interaction: discord.Interaction):
            conn = sqlite3.connect(bot.db.db_file)
            c = conn.cursor()
            c.execute("DELETE FROM players WHERE user_id = ?", (user_id,))
            c.execute("DELETE FROM achievements WHERE user_id = ?", (user_id,))
            c.execute("DELETE FROM inventory WHERE user_id = ?", (user_id,))
            c.execute("DELETE FROM flags WHERE user_id = ?", (user_id,))
            c.execute("DELETE FROM history WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()
            bot.db.create_player(user_id)
            part = bot.story_loader.get_part("PART_01")
            player = bot.db.get_player(user_id)
            embed = bot.create_game_embed(part, player)
            view = StoryView(bot, user_id, part)
            await interaction.response.edit_message(content="✅ تمت إعادة التعيين. ابدأ رحلتك!", embed=embed, view=view)
        
        continue_btn.callback = continue_callback
        reset_btn.callback = reset_callback
        view.add_item(continue_btn)
        view.add_item(reset_btn)
        
        embed = discord.Embed(
            title="⚠️ لديك تقدم سابق",
            description="لديك رحلة مستمرة بالفعل. ماذا تريد أن تفعل؟",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, view=view)
    else:
        bot.db.create_player(user_id)
        part = bot.story_loader.get_part("PART_01")
        if not part:
            await interaction.response.send_message("⚠️ لم يتم العثور على بداية القصة.", ephemeral=True)
            return
        player = bot.db.get_player(user_id)
        embed = bot.create_game_embed(part, player)
        view = StoryView(bot, user_id, part)
        await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="استمر", description="⏩ استمر في رحلتك")
async def continue_game(interaction: discord.Interaction):
    user_id = interaction.user.id
    player = bot.db.get_player(user_id)
    if not player:
        await interaction.response.send_message("❌ لا يوجد تقدم. استخدم `/ابدأ` لبدء رحلة جديدة.", ephemeral=True)
        return
    current_part = player.get("current_part", "PART_01")
    part = bot.story_loader.get_part(current_part)
    if not part:
        part = bot.story_loader.get_part("PART_01")
        bot.db.update_player(user_id, {"current_part": "PART_01"})
        player = bot.db.get_player(user_id)
    embed = bot.create_game_embed(part, player)
    view = StoryView(bot, user_id, part)
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="حالتي", description="📊 اعرض إحصائياتك وإنجازاتك")
async def profile(interaction: discord.Interaction):
    user_id = interaction.user.id
    player = bot.db.get_player(user_id)
    if not player:
        await interaction.response.send_message("❌ لا توجد بيانات. ابدأ بـ /ابدأ", ephemeral=True)
        return
    
    embed = discord.Embed(title=f"👤 ملف المغامر: {interaction.user.name}", color=discord.Color.blue())
    char_stats = (
        f"💎 **الشظايا:** {player['shards']}\n"
        f"🌑 **الفساد:** {player['corruption']}/100\n"
        f"🔮 **الغموض:** {player['mystery']}/100\n"
        f"⭐ **السمعة:** {player['reputation']}\n"
        f"{GameUI.get_alignment_emoji(player['alignment'])} **التوجه:** {player['alignment']}\n"
        f"🤝 **ثقة أرين:** {player['trust_aren']}%\n"
        f"🌍 **استقرار العالم:** {player['world_stability']}%\n"
        f"🌟 **المستوى:** {player['level']} ({player['xp']}/100 XP)"
    )
    embed.description = char_stats
    
    achievements = bot.db.get_achievements(user_id)
    if achievements:
        ach_list = []
        for ach in achievements:
            info = bot.story_loader.get_achievement_info(ach['achievement_id'])
            ach_list.append(f"{info['emoji']} {info['name']}")
        embed.add_field(name="🏆 الإنجازات", value=", ".join(ach_list[:5]), inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="مخزني", description="🎒 اعرض محتويات مخزونك")
async def inventory(interaction: discord.Interaction):
    user_id = interaction.user.id
    items = bot.db.get_inventory(user_id)
    if items:
        desc = ""
        for item in items:
            if item['quantity'] > 1:
                desc += f"• **{item['item_name']}** x{item['quantity']}\n"
            else:
                desc += f"• **{item['item_name']}**\n"
    else:
        desc = "مخزونك فارغ."
    embed = discord.Embed(title=f"🎒 مخزون {interaction.user.name}", description=desc, color=discord.Color.green())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="استخدم", description="🧪 استخدم عنصراً من مخزونك")
@app_commands.describe(العنصر="معرف العنصر (potion, crystal_heart, pure_shard, dark_core)")
async def use_item(interaction: discord.Interaction, العنصر: str):
    user_id = interaction.user.id
    player = bot.db.get_player(user_id)
    if not player:
        await interaction.response.send_message("❌ ابدأ مغامرتك أولاً.", ephemeral=True)
        return
    
    item_id = العنصر.lower()
    if not bot.db.has_item(user_id, item_id, 1):
        await interaction.response.send_message("❌ ليس لديك هذا العنصر.", ephemeral=True)
        return
    
    if item_id == "potion":
        corruption = player['corruption']
        if corruption <= 0:
            await interaction.response.send_message("🌑 الفساد عند أدنى مستوى بالفعل.", ephemeral=True)
            return
        new_corruption = max(0, corruption - 10)
        bot.db.remove_from_inventory(user_id, item_id, 1)
        bot.db.update_player(user_id, {"corruption": new_corruption})
        embed = discord.Embed(title="🧪 استخدمت جرعة نقاء", description=f"🌑 انخفض الفساد بمقدار 10. الفساد الآن {new_corruption}/100", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)
    elif item_id == "crystal_heart":
        stability = player['world_stability']
        if stability >= 100:
            await interaction.response.send_message("🌍 استقرار العالم في أعلى مستوى.", ephemeral=True)
            return
        new_stability = min(100, stability + 10)
        bot.db.remove_from_inventory(user_id, item_id, 1)
        bot.db.update_player(user_id, {"world_stability": new_stability})
        embed = discord.Embed(title="💖 استخدمت قلب الكريستال", description=f"🌍 زاد استقرار العالم بمقدار 10. الاستقرار الآن {new_stability}/100", color=discord.Color.blue())
        await interaction.response.send_message(embed=embed)
    elif item_id == "pure_shard":
        corruption = player['corruption']
        new_corruption = max(0, corruption - 15)
        bot.db.remove_from_inventory(user_id, item_id, 1)
        bot.db.update_player(user_id, {"corruption": new_corruption, "alignment": "Light"})
        embed = discord.Embed(title="✨ استخدمت شظية نقية", description=f"🌑 انخفض الفساد بمقدار 15. أصبحت أكثر نقاءً! التوجه الآن: نور.", color=discord.Color.gold())
        await interaction.response.send_message(embed=embed)
    elif item_id == "dark_core":
        corruption = player['corruption']
        new_corruption = min(100, corruption + 20)
        bot.db.remove_from_inventory(user_id, item_id, 1)
        bot.db.update_player(user_id, {"corruption": new_corruption, "alignment": "Dark"})
        embed = discord.Embed(title="🖤 استخدمت نواة الظلام", description=f"🌑 زاد الفساد بمقدار 20. استسلمت للظلام! التوجه الآن: ظلام.", color=discord.Color.dark_purple())
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("❌ عنصر غير معروف.", ephemeral=True)

@bot.tree.command(name="إنجازاتي", description="🏆 اعرض كل إنجازاتك")
async def achievements(interaction: discord.Interaction):
    user_id = interaction.user.id
    unlocked = {a['achievement_id'] for a in bot.db.get_achievements(user_id)}
    achievements_data = bot.story_loader.data.get("achievements_data", {})
    
    embed = discord.Embed(title=f"🏆 إنجازات {interaction.user.name}", color=discord.Color.gold())
    lines = []
    for ach_id, ach_data in achievements_data.items():
        if ach_id in unlocked:
            lines.append(f"✅ {ach_data.get('emoji', '🏆')} **{ach_data.get('name', ach_id)}**\n└ {ach_data.get('description', '')}")
        else:
            lines.append(f"❌ {ach_data.get('emoji', '🏆')} ~~{ach_data.get('name', ach_id)}~~")
    embed.description = "\n\n".join(lines) if lines else "لا توجد إنجازات محددة."
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="تاريخي", description="📜 اعرض آخر 10 قرارات اتخذتها")
async def history(interaction: discord.Interaction):
    user_id = interaction.user.id
    history_list = bot.db.get_history(user_id, 10)
    if not history_list:
        await interaction.response.send_message("لا يوجد سجل قرارات بعد.", ephemeral=True)
        return
    
    desc = ""
    for h in history_list:
        desc += f"📍 **{h['part_id']}**: {h['choice_text']} → `{h['impact_summary']}`\n"
    embed = discord.Embed(title="📜 سجل قراراتك الأخيرة", description=desc, color=discord.Color.light_grey())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="يومي", description="🎁 احصل على مكافأة يومية")
async def daily(interaction: discord.Interaction):
    user_id = interaction.user.id
    player = bot.db.get_player(user_id)
    if not player:
        bot.db.create_player(user_id)
        player = bot.db.get_player(user_id)
    
    now = datetime.now()
    last = datetime.fromisoformat(player['last_daily']) if player['last_daily'] else now - timedelta(days=1)
    
    if now - last < timedelta(days=1):
        remaining = timedelta(days=1) - (now - last)
        hours, rem = divmod(remaining.seconds, 3600)
        minutes, _ = divmod(rem, 60)
        await interaction.response.send_message(f"⌛ انتظر {hours} ساعة و {minutes} دقيقة للحصول على المكافأة التالية.", ephemeral=True)
        return
    
    bonus_shards = random.randint(1, 5)
    bonus_type = random.randint(1, 100)
    updates = {"shards": player['shards'] + bonus_shards, "last_daily": now.isoformat()}
    impact = f"💎 +{bonus_shards} شظية"
    
    if bonus_type <= 30:
        bot.db.add_to_inventory(user_id, "potion", "🧪 جرعة نقاء", 1)
        impact += " و 🧪 جرعة"
    elif bonus_type <= 45:
        bot.db.add_to_inventory(user_id, "crystal_heart", "💖 قلب الكريستال", 1)
        impact += " و 💖 قلب كريستال"
    elif bonus_type <= 55:
        bot.db.add_to_inventory(user_id, "pure_shard", "✨ شظية نقية", 1)
        impact += " و ✨ شظية نقية"
    elif bonus_type <= 60:
        bot.db.add_to_inventory(user_id, "dark_core", "🖤 نواة الظلام", 1)
        impact += " و 🖤 نواة ظلام"
    
    bot.db.update_player(user_id, updates)
    await interaction.response.send_message(f"🎁 مكافأتك اليومية: {impact}!")

@bot.tree.command(name="إعادة", description="🔄 ابدأ القصة من جديد (احذر: سيحذف كل تقدمك)")
async def reset(interaction: discord.Interaction):
    view = discord.ui.View()
    confirm = discord.ui.Button(label="✅ نعم، احذف كل شيء", style=discord.ButtonStyle.danger)
    cancel = discord.ui.Button(label="❌ لا، تراجع", style=discord.ButtonStyle.secondary)
    
    async def confirm_callback(interaction: discord.Interaction):
        user_id = interaction.user.id
        conn = sqlite3.connect(bot.db.db_file)
        c = conn.cursor()
        c.execute("DELETE FROM players WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM achievements WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM inventory WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM flags WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM history WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        await interaction.response.edit_message(content="✅ تم حذف تقدمك بالكامل. استخدم /ابدأ لبدء رحلة جديدة.", embed=None, view=None)
    
    async def cancel_callback(interaction: discord.Interaction):
        await interaction.response.edit_message(content="❌ تم إلغاء الأمر.", embed=None, view=None)
    
    confirm.callback = confirm_callback
    cancel.callback = cancel_callback
    view.add_item(confirm)
    view.add_item(cancel)
    
    embed = discord.Embed(
        title="⚠️ تأكيد إعادة التعيين",
        description="هل أنت متأكد؟ هذا سيحذف كل تقدمك بشكل نهائي!",
        color=discord.Color.orange()
    )
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="خريطة", description="🗺️ اعرض خريطة العالم")
async def map_command(interaction: discord.Interaction):
    user_id = interaction.user.id
    player = bot.db.get_player(user_id)
    if not player:
        await interaction.response.send_message("❌ ابدأ مغامرتك أولاً.", ephemeral=True)
        return
    
    location = player.get('location', 'أنقاض')
    map_text = """
    ```
    [🌌] العالم الخارجي
       |
    [🏰] المدينة القديمة
       |
    [🌲] الغابة المسحورة
       |
    [🏜️] الصحراء المنسية
       |
    [💎] عالم الكريستال
       |
    [🌑] عالم الظل
    ```
    أنت الآن في: **{}**
    """.format(location)
    
    embed = discord.Embed(title="🗺️ خريطة العوالم", description=map_text, color=discord.Color.green())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="مساعدة", description="📚 عرض المساعدة وشرح الأوامر")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📚 مساعدة رحلة الشظايا",
        description="أهلاً بك في عالم الشظايا! هذا بوت تفاعلي يعتمد على القرارات.",
        color=discord.Color.gold()
    )
    commands_list = (
        "**/ابدأ** - ابدأ رحلة جديدة\n"
        "**/استمر** - استمر في رحلتك\n"
        "**/حالتي** - اعرض إحصائياتك\n"
        "**/مخزني** - اعرض محتويات مخزونك\n"
        "**/استخدم** - استخدم عنصراً (مثل جرعة)\n"
        "**/إنجازاتي** - اعرض الإنجازات\n"
        "**/تاريخي** - اعرض تاريخ قراراتك\n"
        "**/يومي** - احصل على مكافأة يومية\n"
        "**/خريطة** - اعرض خريطة العالم\n"
        "**/إعادة** - ابدأ من جديد (احذر!)\n"
        "**/مساعدة** - عرض هذه المساعدة"
    )
    embed.add_field(name="📋 الأوامر", value=commands_list, inline=False)
    embed.add_field(
        name="🎮 طريقة اللعب",
        value="في كل جزء من القصة، ستظهر لك أزرار تمثل الخيارات المتاحة. اختر ما يناسبك، وكل قرار يؤثر على شخصيتك والعالم من حولك.\n\n**🧪 الجرعات**: يمكنك الحصول على جرعات من المكافآت اليومية، واستخدامها لتقليل الفساد أو تحسين استقرار العالم.",
        inline=False
    )
    await interaction.response.send_message(embed=embed)

# ============================================
# حدث اتصال البوت
# ============================================
@bot.event
async def on_ready():
    logger.info(f"✅ {bot.user} متصل وجاهز!")
    logger.info(f"🌐 في {len(bot.guilds)} سيرفر")
    await bot.change_presence(activity=discord.Game(name="/ابدأ لبدء الرحلة"))

# ============================================
# تشغيل البوت
# ============================================
if __name__ == "__main__":
    keep_alive()
    TOKEN = os.getenv('TOKEN')
    if TOKEN:
        try:
            bot.run(TOKEN)
        except Exception as e:
            logger.critical(f"🚨 خطأ في تشغيل البوت: {e}")
    else:
        logger.critical("🚨 التوكن غير موجود! ضع التوكن في متغير البيئة TOKEN")
