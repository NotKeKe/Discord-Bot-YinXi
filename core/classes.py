from discord.ext import commands

bot:commands.Bot = None

class Cog_Extension(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.global_bot()
    
    def global_bot(self):
        global bot
        bot = self.bot