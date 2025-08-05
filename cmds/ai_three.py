import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
import logging
from motor.motor_asyncio import AsyncIOMotorClient
import io

from core.functions import MONGO_URL, create_basic_embed, UnixNow
from core.classes import Cog_Extension
from core.translator import locale_str
from cmds.ai_chat.chat.chat import Chat
from cmds.ai_chat.chat import gener_title
from cmds.ai_chat.tools.map import image_generate, video_generate
from cmds.ai_chat.utils import model, chat_history_autocomplete, model_autocomplete

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
            model: str = 'qwen-3-32b', 
            history: str = None, 
            enable_tools: bool = True, 
            image: discord.Attachment = None, 
            text_file: discord.Attachment = None,
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
                ls_history = result.get('messages')
                

            async with ctx.typing():
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

                embed = create_basic_embed(title='AI文字生成', description=result, color=ctx.author.color)
                embed.set_footer(text=f'Powered by {model}')

                msg = await ctx.send(embed=embed)

            if history:
                await collection.update_one({'title': history}, {'$set': {'messages': complete_history}}, upsert=True)
            else:
                title = await gener_title(complete_history)
                await collection.insert_one({
                    'title': title,
                    'messages': complete_history,
                    'createAt': UnixNow()
                })

            if think:
                button = discord.ui.Button(label='思考過程', style=discord.ButtonStyle.blurple)  
                async def button_callback(interaction: discord.Interaction, button):
                    if think >= 1999:
                        bytes_io = io.BytesIO(think.encode())
                        file = discord.File(bytes_io, filename='think.txt')

                        await interaction.response.send_message(file=file, ephemeral=True)
                    else:
                        await interaction.response.send_message(think)

                button.callback = button_callback

                view = discord.ui.View()
                view.add_item(button)

                await msg.edit(view=view)
        except:
            logger.error('Error accured at chat command', exc_info=True)

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
                embed = create_basic_embed(title='AI圖片生成', color=ctx.author.color)
                embed.set_image(url=url)
                embed.add_field(name='花費時間(秒)', value=int(time))
                embed.set_footer(text=f'Powered by {model}')
                await ctx.send(embed=embed)
            except:
                await ctx.send('生成失敗', ephemeral=True)

    @commands.hybrid_command(name='影片生成', description='Generate a video')
    @app_commands.choices(
        model=[Choice(name='cogvideox-flash', value='cogvideox-flash')],
        size = [
            Choice(name=size, value=size) 
            for size in ('720x480', '1024x1024', '1280x960', '960x1280', '1920x1080', '1080x1920', '2048x1080', '3840x2160')
        ],
        fps = [
            Choice(name=30, value=30),
            Choice(name=60, value=60)
        ],
        是否要聲音 = [
            Choice(name='要', value=1),
            Choice(name='不要', value=0)
        ]
    )
    @app_commands.describe(fps='預設為60，可選30 or 60', 影片時長='單位為秒, 預設為5, 最高為10')
    async def _video_generate(
            self, ctx: commands.Context, * , 
            輸入文字: str, 
            圖片連結: str = None, 
            size: str = None, 
            fps: int = 60, 
            是否要聲音: int = True, 
            影片時長: int = 5, 
            model: str = 'cogvideox-flash'
        ):
        try:
            async with ctx.typing():
                if 影片時長 > 10:
                    await ctx.send(f'最高只能幫你生成10秒的圖片 要怪就怪{model}...', ephemeral=True) 
                    影片時長 = 10

                if fps not in (30, 60):
                    fps = 60

                try: 是否要聲音 = bool(是否要聲音)
                except: return await ctx.send(locale_str('send_video_generate_wrong_type'))

                url = await video_generate(輸入文字, 圖片連結, size, fps, 是否要聲音, 影片時長)
                string = f'影片生成 (Power by {model}) \n {url}'
                await ctx.send(string)
        except Exception as e:
            await ctx.send(f'生成失敗, reason: {e}', ephemeral=True)

async def setup(bot):
    await bot.add_cog(AIChat(bot))