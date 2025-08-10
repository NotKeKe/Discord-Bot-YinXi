import discord
from discord import app_commands
from discord.ext import commands
import logging
from motor.motor_asyncio import AsyncIOMotorClient
import openai

from core.functions import MONGO_URL, create_basic_embed, current_time, get_attachment, split_str_by_len_and_backtick, UnixNow
from core.classes import Cog_Extension, get_bot
from core.translator import locale_str, load_translated
from cmds.ai_chat.on_msg import ai_channel_chat, chat_human_chat
from cmds.ai_chat.utils import model_autocomplete, to_user_message, to_assistant_message, add_think_button, add_history_button, split_provider_model

logger = logging.getLogger(__name__)

# db = db_client['aichannel_chat_history']
db_key = 'aichannel_chat_history'

async def to_history(channel: discord.TextChannel, limit: int = 10):
    histories = []
    messages = [m async for m in channel.history(limit=limit)]
    messages.reverse()
    pre = str()

    bot = get_bot()
    
    for m in messages:
        if m.author == bot.user:
            if m.content == '嘗試重啟bot...': continue
            if pre == 'bot':
                histories[-1]['content'] += m.content + '\n'
            else:
                histories.extend(to_assistant_message(m.content + '\n'))
            pre = 'bot'
        else:
            if m.content.startswith('['): continue
            content = '`user_name: {userName}; at: {time}` said: 「{mcontent}」\n'.format(userName=m.author.global_name, mcontent=m.content, time=m.created_at.strftime('%Y-%m-%d %H:%M:%S')) if not channel.guild else '`user_name: {userName}; at: {time}` said: {mcontent}'.format(userName=m.author.global_name, mcontent=m.content, time=m.created_at.strftime('%Y-%m-%d %H:%M:%S'))
            if pre == 'user':
                histories[-1]["content"] = content + '\n'
            else:
                attachment = get_attachment(m)
                msg = (
                    content,
                    current_time(),
                    f"The following are urls provided by user: {'\n'.join(attachment)}" if attachment else ''
                )
                histories.extend(to_user_message('\n\n'.join(msg)))
            pre = 'user'

    return histories[-6:]

class AIChannelTwo(Cog_Extension):
    def __init__(self, bot):
        super().__init__(bot)
        self.db_client = AsyncIOMotorClient(MONGO_URL)
        self.db = self.db_client[db_key]

    async def cog_load(self):
        print(f'已載入{__name__}')

    async def cog_unload(self):
        if self.db_client:
            self.db_client.close()

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        await self.on_msg_ai_channel(msg)
        await self.on_msg_chat_human(msg)

    async def on_msg_chat_human(self, msg: discord.Message):
        if not msg.content and not msg.attachments: return
        if msg.author.bot: return
        if msg.content.startswith('[') or msg.content.startswith('[! '): return

        try:
            ctx = await self.bot.get_context(msg)

            if ctx.guild:
                db = self.db_client['chat_human_setting']
                collection = db[str(ctx.channel.id)]

                init_data = await collection.find_one({'_id': 'chat_human_setting'})
                if not init_data: return

            async with ctx.typing():
                urls = get_attachment(msg)

                think, result = await chat_human_chat(ctx, msg.content, (await to_history(msg.channel)), urls)

                ls = result.split('。')

                for item in ls:
                    if not item: continue
                    msg = await ctx.send(item)

            view = discord.ui.View()
            await add_think_button(msg, view, think)

            timeout = await view.wait()
            if timeout: await msg.edit(view=None)
        except openai.BadRequestError as e:
            logger.error('Error accured at on_msg_chat_human', exc_info=True)
            await ctx.send(f'Error accured :<\n{str(e)}', ephemeral=True)
        except:
            logger.error('Error accured at on_msg_chat_human', exc_info=True)
            await msg.channel.send(await self.bot.tree.translator.get_translate('send_on_msg_chat_human_error'))

    async def on_msg_ai_channel(self, msg: discord.Message):
        if not msg.content and not msg.attachments: return
        if msg.author.bot: return
        if msg.content.startswith('[') or msg.content.startswith('[! '): return

        try:
            ctx = await self.bot.get_context(msg)
        
            db = self.db
            collection = db[str(ctx.channel.id)]

            init_data = await collection.find_one({'_id': 'ai_channel_setting'})
            if not init_data: return

            async with ctx.typing():
                model = init_data.get('model')
                provider = init_data.get('provider')
                system_prompt = init_data.get('system_prompt')
                urls = get_attachment(msg)

                final_model = f'{provider}:{model}'

                think, result, complete_history = await ai_channel_chat(ctx, msg.content, final_model, system_prompt, urls)

                ls = split_str_by_len_and_backtick(result, 1999)

                for item in ls:
                    if not item: continue
                    msg = await ctx.send(item)
            
            view = discord.ui.View()
            await add_history_button(msg, view, complete_history)
            await add_think_button(msg, view, think)
            
            timeout = await view.wait()
            if timeout: await msg.edit(view=None)
        except openai.BadRequestError as e:
            logger.error('Error accured at on_msg_ai_channel', exc_info=True)
            await ctx.send(f'Error accured :<\n{str(e)}', ephemeral=True)
        except:
            logger.error('Error accured at on_msg_ai_channel', exc_info=True)
            await msg.channel.send(await self.bot.tree.translator.get_translate('send_on_msg_ai_channel_error'))

    @commands.hybrid_command(name=locale_str('set_ai_channel'), description=locale_str('set_ai_channel'))
    @commands.has_permissions(administrator=True)
    @app_commands.autocomplete(model=model_autocomplete)
    async def set_ai_channel(self, ctx: commands.Context, model: str = None, system_prompt: str = None):
        try:
            async with ctx.typing():
                db = self.db
                collection = db[str(ctx.channel.id)]

                channel_exist = await collection.find_one({'_id': 'ai_channel_setting'})

                if channel_exist:
                    if model or system_prompt:
                        if system_prompt: await ctx.invoke(self.bot.get_command('change_ai_channel_system_prompt'), system_prompt=system_prompt)
                        if model: await ctx.invoke(self.bot.get_command('change_ai_channel_model'), model=model)
                        return
                    else:
                        return await ctx.send(await ctx.interaction.translate('send_set_ai_channel_channel_exist'))
                    
                if model is None:
                    model = 'qwen-3-32b'

                provider, model = split_provider_model(model)
                    
                await collection.insert_one(
                    {
                        '_id': 'ai_channel_setting',
                        'provider': provider,
                        'model': model,
                        'channel': ctx.channel.id,
                        'initial_member': ctx.author.id,
                        'system_prompt': system_prompt,
                        'createAt': UnixNow()
                    }
                )
                await ctx.send((await ctx.interaction.translate('send_set_ai_channel_success')).format(model))
                # await ctx.send('good')
        except:
            logger.error('Error accured at set_ai_channel command', exc_info=True)

    @commands.hybrid_command(name=locale_str('cancel_ai_channel'), description=locale_str('cancel_ai_channel'))
    @commands.has_permissions(administrator=True)
    async def cancel_ai_channel(self, ctx: commands.Context):
        try:
            async with ctx.typing():
                db = self.db
                collection = db[str(ctx.channel.id)]

                if not (await collection.find_one({'_id': 'ai_channel_setting'})):
                    return await ctx.send(await ctx.interaction.translate('cancel_ai_channel_channel_not_found'))
                
                '''i18n'''
                button_check_text = await ctx.interaction.translate('button_cancel_ai_channel_check')
                button_refuse_text = await ctx.interaction.translate('button_cancel_ai_channel_refuse')
                eb = load_translated(await ctx.interaction.translate('embed_cancel_ai_channel_whether_cancel'))[0]
                eb_title = eb.get('title')
                ''''''

                view = discord.ui.View()
                button_check = discord.ui.Button(label=button_check_text, style=discord.ButtonStyle.blurple, emoji='✅')
                button_refuse = discord.ui.Button(label=button_refuse_text, style=discord.ButtonStyle.blurple, emoji='❌')

                async def button_check_callback(interaction: discord.Interaction):
                    msg = interaction.message
                    await collection.drop()
                    await interaction.response.send_message(await interaction.translate('send_cancel_ai_channel_button_check_success'))
                    await msg.edit(view=None)

                async def button_refuse_callback(interaction: discord.Interaction):
                    msg = interaction.message
                    await interaction.response.send_message(await interaction.translate('send_cancel_ai_channel_button_check_cancel'))
                    await msg.edit(view=None)

                button_check.callback = button_check_callback
                button_refuse.callback = button_refuse_callback
                view.add_item(button_check)
                view.add_item(button_refuse)

                eb = create_basic_embed('❓' + eb_title)

                await ctx.send(embed=eb, view=view)
        except:
            logger.error('Error accured at cancel_ai_channel', exc_info=True)

    @commands.hybrid_command(name=locale_str('change_ai_channel_model'), description=locale_str('change_ai_channel_model'))
    @commands.has_permissions(administrator=True)
    @app_commands.autocomplete(model=model_autocomplete)
    async def change_ai_channel_model(self, ctx: commands.Context, model: str):
        try:
            async with ctx.typing():
                db = self.db
                collection = db[str(ctx.channel.id)]

                provider, model = split_provider_model(model)

                async def check_model():
                    db = self.db_client['aichat_available_models']
                    collection = db['models']

                    _id = 'model_setting'
                    data = await collection.find_one({'_id': _id})
                    models = set([m for models in data.values() for m in models if m != _id])

                    return model in models
                
                if not (await check_model()):
                    return await ctx.send(await ctx.interaction.translate('send_change_ai_channel_model_not_available_model'.format(model=model)))

                if not (await collection.find_one({'_id': 'ai_channel_setting'})):
                    return await ctx.send(await ctx.interaction.translate('send_change_ai_channel_model_channel_not_found'))
                
                await collection.update_one({'_id': 'ai_channel_setting'}, {'$set': {'model': model, 'provider': provider}})
                
                await ctx.send((await ctx.interaction.translate('send_change_ai_channel_model_successfully_change_model')).format(model=model))
        except:
            logger.error('Error accured at change_ai_channel_model: ', exc_info=True)

    @commands.hybrid_command(name=locale_str('change_ai_channel_system_prompt'), description=locale_str('change_ai_channel_system_prompt'))
    @commands.has_permissions(administrator=True)
    async def change_ai_channel_system_prompt(self, ctx: commands.Context, system_prompt: str):
        try:
            async with ctx.typing():
                db = self.db
                collection = db[str(ctx.channel.id)]

                if not (await collection.find_one({'_id': 'ai_channel_setting'})):
                    return await ctx.send(await ctx.interaction.translate('send_change_ai_channel_system_prompt_channel_not_found'))
                
                await collection.update_one({'_id': 'ai_channel_setting'}, {'$set': {'system_prompt': system_prompt.strip()}})
                
                await ctx.send((await ctx.interaction.translate('send_change_ai_channel_system_prompt_successfully_change_system_prompt')).format(system_prompt=system_prompt))
        except:
            logger.error('Error accured at change_ai_channel_system_prompt: ', exc_info=True)

    @commands.hybrid_command(name=locale_str('show_ai_channel_model'), description=locale_str('show_ai_channel_model'))
    async def model_show(self, ctx: commands.Context):
        try:
            async with ctx.typing():
                db = self.db
                collection = db[str(ctx.channel.id)]

                data = await collection.find_one({'_id': 'ai_channel_setting'})
                if not data:
                    return await ctx.send(await ctx.interaction.translate('send_show_ai_channel_model_channel_not_found'))
                model = data.get('model')
                
                await ctx.send((await ctx.interaction.translate('send_show_ai_channel_model_model')).format(model=model))
        except:
            logger.error('Error accured at show_ai_channel_model: ', exc_info=True)

    @commands.hybrid_command(name=locale_str('set_chat_human'), description=locale_str('set_chat_human'))
    @commands.has_permissions(administrator=True)
    async def set_chat_human(self, ctx: commands.Context):
        try:
            async with ctx.typing():
                db = self.db_client['chat_human_setting']
                collection = db[str(ctx.channel.id)]

                channel_exist = await collection.find_one({'_id': 'chat_human_setting'})

                if channel_exist:
                    return await ctx.send(await ctx.interaction.translate('send_set_chat_human_channel_exist'))
                    
                await collection.insert_one(
                    {
                        '_id': 'chat_human_setting',
                        'initial_member': ctx.author.id,
                        'createAt': UnixNow()
                    }
                )
                # await ctx.send(locale_str('send_set_chat_human_success').format(model))
                await ctx.send('good')
        except:
            logger.error('Error accured at set_chat_human command', exc_info=True)

    @commands.hybrid_command(name=locale_str('cancel_chat_human'), description=locale_str('cancel_chat_human'))
    @commands.has_permissions(administrator=True)
    async def cancel_chat_human(self, ctx: commands.Context):
        try:
            async with ctx.typing():
                db = self.db_client['chat_human_setting']
                collection = db[str(ctx.channel.id)]

                if not (await collection.find_one({'_id': 'chat_human_setting'})):
                    return await ctx.send(await ctx.interaction.translate('cancel_chat_human_channel_not_found'))
                
                '''i18n'''
                button_check_text = await ctx.interaction.translate('button_cancel_chat_human_check')
                button_refuse_text = await ctx.interaction.translate('button_cancel_chat_human_refuse')
                eb = load_translated(await ctx.interaction.translate('embed_cancel_chat_human_whether_cancel'))[0]
                eb_title = eb.get('title')
                ''''''

                view = discord.ui.View()
                button_check = discord.ui.Button(label=button_check_text, style=discord.ButtonStyle.blurple, emoji='✅')
                button_refuse = discord.ui.Button(label=button_refuse_text, style=discord.ButtonStyle.blurple, emoji='❌')

                async def button_check_callback(interaction: discord.Interaction):
                    msg = interaction.message
                    await collection.drop()
                    await interaction.response.send_message(await interaction.translate('send_cancel_chat_human_button_check_success'))
                    await msg.edit(view=None)

                async def button_refuse_callback(interaction: discord.Interaction):
                    msg = interaction.message
                    await interaction.response.send_message(await interaction.translate('send_cancel_chat_human_button_check_cancel'))
                    await msg.edit(view=None)

                button_check.callback = button_check_callback
                button_refuse.callback = button_refuse_callback
                view.add_item(button_check)
                view.add_item(button_refuse)

                eb = create_basic_embed('❓' + eb_title)

                await ctx.send(embed=eb, view=view)
        except:
            logger.error('Error accured at cancel_chat_human', exc_info=True)

async def setup(bot):
    await bot.add_cog(AIChannelTwo(bot))