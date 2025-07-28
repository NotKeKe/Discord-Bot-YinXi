from discord.app_commands import Translator, locale_str, TranslationContext, TranslationContextLocation  
from discord.ext import commands
import discord
import aiofiles
import orjson
import aiosqlite
import traceback

from core.mock_interaction import MockInteraction

DEFAULT_LANG = 'zh-TW'

class i18n(Translator):
    def __init__(self):
        super().__init__()
        self.translations = {}
        example = {
            # 註: 此處的指令名稱應該都要是英文，並且與en-US.json中的指令名稱相同
            'lang': {
                'name': { # 命名規則: "指令名稱"
                    'command_1': str(),
                    'command_2': str()
                },
                'description': { # 命名規則: "指令名稱"
                    'command_1': str(),
                    'command_2': str()
                },
                'params_desc': { # 命名規則: "指令名稱_參數名稱"
                    'command1_param': str(),
                    'command2_param': str()
                },
                'components': { # 命名規則: "{功能: send, embed, button, select}_指令名稱_對於該功能的`英文`描述"
                    'send_command1_DESCRIPTIONHERE': str(),
                    'send_command2_DESCRIPTIONHERE': str(),
                    'embed_command1_DESCRIPTIONHERE': [
                        {
                            'title': str(),
                            'description': str(),
                            'field': [
                                {
                                    'name': str(),
                                    'value': str()
                                }
                            ],
                            'footer': str(),
                            'author': str()
                        }
                    ],
                    'embed_command2_DESCRIPTIONHERE': [...],

                    # 以下尚未決定如何翻譯
                    'button_command1_DESCRIPTIONHERE': str(),
                    'button_command2_DESCRIPTIONHERE': str()
                }
            }
        }

    async def get_translate(self, string: str, lang_code: str = None, ctx: commands.Context = None):
        """這是一個能夠透過 lang code 與指定 key 來獲得翻譯的方法，因為 translate 會被 interaction.translate 呼叫，但不一定每個 ctx 都有 interaction (我不確定，但我的理解是這樣)。

        Args:
            string (str): 在此處傳入 key
            lang_code (str): 在此處傳入使用者偏好語言，例如: zh-TW
        """        
        lang_pref = None

        '''Get user prefer lang if exist'''
        if ctx: 
            lang_pref = await get_user_lang(ctx.author.id)
        ''''''

        lang_code = lang_pref or lang_code

        if not lang_code: lang_code = DEFAULT_LANG
        
        locale_item = self.translations.get(lang_code, {})  

        item = locale_item.get('components', {})
        return_item = item.get(string, string)

        if isinstance(return_item, list):
            return orjson.dumps(return_item).decode('utf-8')
        elif isinstance(return_item, str):
            return return_item
        else:
            return string

    async def translate(self, string: locale_str, locale: discord.Locale, context: TranslationContext):
        lang = None

        '''Get user prefer lang if exist'''
        user_id = None
        if hasattr(context.data, 'user'):  
            user_id = context.data.user.id  
        elif hasattr(context.data, 'author'):  
            user_id = context.data.author.id  
        elif hasattr(context.data, 'id'):
            user_id = context.data.id
        # print(user_id)
        if user_id: 
            lang = await get_user_lang(user_id)
        ''''''

        lang = lang or locale.value

        locale_item = self.translations.get(locale.value, {})  
        if not locale_item:
            locale_item = self.translations.get(DEFAULT_LANG, {})

        if context.location == TranslationContextLocation.command_name:
            # string.message = command_name
            name = locale_item.get('name', {})
            return_item = name.get(string.message, string.message)
        elif context.location == TranslationContextLocation.command_description:
            desc = locale_item.get('description', {})
            return_item = desc.get(string.message, string.message)
        elif context.location == TranslationContextLocation.parameter_description:
            params = locale_item.get('params_desc', {})
            return_item = params.get(string.message, string.message)
        else:
            # This may return a list
            item = locale_item.get('components', {})
            return_item = item.get(string.message, string.message)

        if isinstance(return_item, list):
            return orjson.dumps(return_item).decode('utf-8')
        elif isinstance(return_item, str):
            return return_item
        else:
            return string.message
    
    async def load(self, lang: str = None):
        langs = [lang] if lang else ('en-US', 'zh-TW', 'zh-CN')
        for l in langs:
            try:
                async with aiofiles.open(f'./core/locales/{l}.json', 'rb') as f:
                    self.translations[l] = orjson.loads(await f.read())
                    print(f'Successfully loaded {l} (translator)')
            except:
                traceback.print_exc()
                print(f'Failed to load {l} (translator)')

        # load user's lang.db
        async with aiosqlite.connect('./data/user_lang.db') as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE,
                    lang TEXT
                )''')
            await db.commit()

    async def unload(self, lang: str = None):
        if lang:
            del self.translations[lang]
        else:
            self.translations.clear()

    async def reload(self, lang: str = None):
        await self.unload(lang)
        await self.load(lang)


def load_translated(item: str):
    return orjson.loads(item.encode('utf-8'))

async def get_user_lang(user_id: int):
    async with aiosqlite.connect('./data/user_lang.db') as db:
        cursor = await db.execute('SELECT lang FROM users WHERE user_id = ?', (user_id,))
        result = await cursor.fetchone()
        if result:
            # print(result[0] + (user_id))
            return result[0]
        else:
            return None