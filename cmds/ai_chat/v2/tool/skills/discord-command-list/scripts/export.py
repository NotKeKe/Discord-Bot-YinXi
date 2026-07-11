import inspect
from typing import Literal, Any

from core.classes import get_bot

class Tool:
    def call(
        self,
        action: Literal['list_cogs', 'list_commands', 'search', 'get_command_info'],
        keyword: str = '',
        command_name: str = ''
    ) -> str:
        bot = get_bot()

        match action:
            case 'list_cogs':
                return '\n'.join(bot.cogs.keys())

            case 'list_commands':
                result = []
                for cog_name, cog in bot.cogs.items():
                    cmds = [c.name for c in cog.get_commands()]
                    if cmds:
                        result.append(f'{cog_name}: {", ".join(cmds)}')
                return '\n'.join(result)

            case 'search':
                kw = keyword.lower().strip()
                if not kw:
                    return 'Please provide a keyword.'
                result = []
                for cog_name, cog in bot.cogs.items():
                    if kw in cog_name.lower():
                        result.append(f'[COG] {cog_name}')
                    for cmd in cog.get_commands():
                        if kw in cmd.name.lower():
                            result.append(f'[CMD] {cog_name}.{cmd.name}')
                return '\n'.join(result) if result else 'No matching results found.'

            case 'get_command_info':
                if not command_name:
                    return 'Please provide a command name.'
                cmd = bot.get_command(command_name)
                if not cmd:
                    return f'Command not found: {command_name}'

                translator: Any = bot.tree.translator
                if not translator:
                    return f'Command not found: {command_name} (translator not loaded)'
                translations = translator.translations.get('zh-TW', {})
                cmd_name_t = translations.get('name', {}).get(command_name, command_name)
                cmd_desc_t = translations.get('description', {}).get(command_name, '(no description)')

                lines = [f'Name: {cmd_name_t}', f'Description: {cmd_desc_t}']

                params = list(inspect.signature(cmd.callback).parameters.values())[1:]
                if params:
                    lines.append('Parameters:')
                    for p in params:
                        param_desc = translations.get('params_desc', {}).get(
                            f'{command_name}_{p.name}', ''
                        )
                        required = p.default is inspect.Parameter.empty
                        lines.append(f'  - {p.name} (required: {required}): {param_desc}')

                return '\n'.join(lines)