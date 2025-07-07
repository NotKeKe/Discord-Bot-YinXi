from discord.app_commands import Translator, locale_str, TranslationContext, TranslationContextLocation  
import discord
import aiofiles
import orjson
import traceback

class i18n(Translator):
    def __init__(self):
        super().__init__()
        self.translations = {}
        example = {
            # 註: 此處的指令名稱應該都要是英文，並且與en-US.json中的指令名稱相同
            'lang': {
                'name': { # 命名規則: 指令名稱
                    'command_1': str(),
                    'command_2': str()
                },
                'description': { # 命名規則: 指令名稱
                    'command_1': str(),
                    'command_2': str()
                },
                'params_desc': { # 命名規則: 指令名稱_參數名稱
                    'command1_param': str(),
                    'command2_param': str()
                },
                'components': { # 命名規則: {功能: send, embed, button, select}_指令名稱_對於該功能的`英文`描述
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

    async def translate(self, string: locale_str, locale: discord.Locale, context: TranslationContext):
        # locale_translations = self.translations.get(locale.value, {})  
        # return locale_translations.get(string.message, string.message)
        '''Get user prefer lang if exist'''
        user_id = None
        if hasattr(context.data, 'user'):  
            user_id = context.data.user.id  
        elif hasattr(context.data, 'author'):  
            user_id = context.data.author.id  
        
        if user_id: pass
            # TODO: 在此處連接本地 json / db 去儲存使用者偏好語言
        ''''''

        locale_item = self.translations.get(locale.value, {})  
        if not locale_item:
            locale_item = self.translations.get('zh-TW', {})

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