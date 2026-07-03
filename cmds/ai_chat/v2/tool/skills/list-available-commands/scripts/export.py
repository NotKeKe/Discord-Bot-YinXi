from core.classes import get_bot

class Tool:
    def call(self) -> str:
        result = []
        bot = get_bot()
        cogs = bot.cogs

        for cog in list(cogs.values()):
            cmds = cog.get_commands()
            result.append(str({cog.__cog_name__: [c.name for c in cmds]}))

        return '\n'.join(result)
