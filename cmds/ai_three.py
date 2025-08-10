import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
import openai

from core.functions import MONGO_URL, create_basic_embed, UnixNow
from core.classes import Cog_Extension
from core.translator import locale_str, load_translated
from cmds.ai_chat.chat.chat import Chat
from cmds.ai_chat.chat import gener_title
from cmds.ai_chat.tools.map import image_generate, video_generate
from cmds.ai_chat.utils import model, chat_history_autocomplete, model_autocomplete, add_history_button, add_think_button

logger = logging.getLogger(__name__)

# db = db_client['aichat_chat_history']
# 命名方式: 'ClassName_FunctionName_功能'
db_key = 'aichat_chat_history'

class AIChat(Cog_Extension):
    def __init__(self, bot):
        super().__init__(bot)
        self.db_client = AsyncIOMotorClient(MONGO_URL)
        self.db = self.db_client[db_key]

    async def cog_unload(self):
        if self.db_client:
            self.db_client.close()

    @commands.Cog.listener()
    async def on_ready(self):
        await model.fetch_models()

    @commands.hybrid_command(name=locale_str('chat'), description=locale_str('chat'))
    @app_commands.describe(is_vision_model = locale_str('chat_is_vision_model'))
    @app_commands.autocomplete(
        model = model_autocomplete,
        history = chat_history_autocomplete
    )
    async def chat(
            self, 
            ctx: commands.Context, 
            prompt: str, 
            model: str = 'cerebras:gpt-oss-120b', 
            history: str = None, 
            enable_tools: bool = True, 
            image: Optional[discord.Attachment] = None, 
            text_file: Optional[discord.Attachment] = None,
            is_vision_model: bool = False
        ):
        try:
            db = self.db
            collection = db[str(ctx.author.id)]

            ls_history = None
            if history:
                result = await collection.find_one({
                    'title': history
                })
                if not result: return await ctx.send(f'Unknow error, cannot found any title called `{history}`')
                ls_history = result.get('messages')
                
            await ctx.defer()

            client = Chat(
                ctx=ctx,
                model=model
            )

            think, result, complete_history = await client.chat(
                prompt=prompt, 
                is_vision_model=is_vision_model, 
                history=ls_history, 
                is_enable_tools=enable_tools, 
                image=image, 
                text_file=text_file
            )

            '''i18n'''
            eb = load_translated(await ctx.interaction.translate('embed_chat'))[0]
            eb_title = eb.get('title')
            ''''''

            embed = create_basic_embed(title=eb_title, description=result, color=ctx.author.color)
            embed.set_footer(text=f'Powered by {model}')

            msg = await ctx.send(embed=embed)

            view = discord.ui.View()
            await add_history_button(msg, view, complete_history)
            await add_think_button(msg, view, think)

            if result:
                if history:
                    await collection.update_one({'title': history}, {'$set': {'messages': complete_history}}, upsert=True)
                else:
                    title = await gener_title(complete_history)
                    await collection.insert_one({
                        'title': title,
                        'messages': complete_history,
                        'createAt': UnixNow()
                    })

            timeout = await view.wait()
            if timeout: await msg.edit(view=None)
        except openai.BadRequestError as e:
            logger.error('Error accured at chat command', exc_info=True)
            await ctx.send(f'Error accured :<\n{str(e)}', ephemeral=True)
        except:
            logger.error('Error accured at chat command', exc_info=True)
            await ctx.send('Error accured :<', ephemeral=True)

    @commands.hybrid_command(name=locale_str('image_generate'), description=locale_str('image_generate'))
    @app_commands.choices(
        model=[
            Choice(name='cogview-3-flash', value='cogview-3-flash')
        ]
    )
    async def _image_gener(self, ctx: commands.Context, prompt: str, model: str = 'cogview-3-flash'):
        async with ctx.typing():
            try:
                url, time = await image_generate(prompt, model)

                '''i18n'''
                eb = load_translated(await ctx.interaction.translate('embed_image_generate'))[0]
                eb_title = eb.get('title')
                eb_field_1 = (eb.get('fields'))[0]
                field_name = eb_field_1.get('name')
                ''''''

                embed = create_basic_embed(title=eb_title, color=ctx.author.color)
                embed.set_image(url=url)
                embed.add_field(name=field_name, value=int(time))
                embed.set_footer(text=f'Powered by {model}')
                await ctx.send(embed=embed)
            except:
                await ctx.send(await ctx.interaction.translate('send_image_generate_fail'), ephemeral=True)

    @commands.hybrid_command(name=locale_str('video_generate'), description=locale_str('video_generate'))
    @app_commands.choices(
        model=[Choice(name='cogvideox-flash', value='cogvideox-flash')],
        size = [
            Choice(name=size, value=size) 
            for size in ('720x480', '1024x1024', '1280x960', '960x1280', '1920x1080', '1080x1920', '2048x1080', '3840x2160')
        ],
        fps = [
            Choice(name=30, value=30),
            Choice(name=60, value=60)
        ]
    )
    @app_commands.describe(
        prompt=locale_str('video_generate_prompt'),
        image_url=locale_str('video_generate_image_url'),
        size=locale_str('video_generate_size'),
        fps=locale_str('video_generate_fps'),
        has_audio=locale_str('video_generate_has_audio'),
        duration=locale_str('video_generate_duration'),
        model=locale_str('video_generate_model')
    )
    async def _video_generate(
            self, ctx: commands.Context, *,
            prompt: str,
            image_url: str = None,
            size: str = None,
            fps: int = 60,
            has_audio: bool = True,
            duration: int = 5,
            model: str = 'cogvideox-flash'
        ):
        try:
            async with ctx.typing():
                if duration > 10:
                    await ctx.send(await ctx.interaction.translate('send_video_generate_duration_too_long').format(model=model), ephemeral=True)
                    duration = 10

                if fps not in (30, 60):
                    fps = 60

                try:
                    has_audio = bool(has_audio)
                except:
                    return await ctx.send(await ctx.interaction.translate('send_video_generate_wrong_type'))

                url, time = await video_generate(prompt, image_url, size, fps, has_audio, duration)
                string = (await ctx.interaction.translate('send_video_generate_success')).format(model=model, url=url, time=int(time))
                await ctx.send(string)
        except Exception as e:
            await ctx.send((await ctx.interaction.translate('send_video_generate_fail')).format(e=e), ephemeral=True)

async def setup(bot):
    await bot.add_cog(AIChat(bot))