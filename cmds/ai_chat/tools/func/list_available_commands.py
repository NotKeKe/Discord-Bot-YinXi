from core.classes import get_bot

def list_available_commands() -> str:
    """Return all of bot's commands
    """ 
    result = []

    bot = get_bot()
    cogs = bot.cogs

    for cog in list(cogs.values()):
        cmds = cog.get_commands()
        result.append(str({cog.__cog_name__: [c.name for c in cmds]}))
        
    return '\n'.join(result)