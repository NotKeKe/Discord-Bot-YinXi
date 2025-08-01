from discord.ext import commands

bot: commands.Bot = None

def set_bot(bot_instance: commands.Bot):
    """設定全域 bot 實例"""
    global bot
    bot = bot_instance

def get_bot() -> commands.Bot:
    """取得全域 bot 實例"""
    return bot

class Cog_Extension(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot