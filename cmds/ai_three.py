import discord
from discord import app_commands
from discord.ext import commands
import logging
from motor.motor_asyncio import AsyncIOMotorClient
import io

from core.functions import testing_guildID, is_testing_guild, MONGO_URL, create_basic_embed, split_str_by_len, UnixNow
from core.classes import Cog_Extension
from core.translator import locale_str
from cmds.ai_chat.chat.chat import Chat
from cmds.ai_chat.chat import gener_title
from cmds.ai_chat.utils import model, history_autocomplete, model_autocomplete

logger = logging.getLogger(__name__)

availble_models = []

# db = db_client['ai_chat_chat_history']
# 命名方式: 'ClassName_FunctionName_功能'

class AIChat(Cog_Extension):
    @commands.Cog.listener()
    async def on_ready(self):
        await model.fetch_models()

    @commands.hybrid_command(name=locale_str('chat'), description=locale_str('chat'))
    @app_commands.guilds(discord.Object(testing_guildID))
    @app_commands.describe(is_vision_model = locale_str('chat_is_vision_model'))
    @app_commands.autocomplete(
        model = model_autocomplete,
        history = history_autocomplete
    )
    async def chat(
            self, 
            ctx: commands.Context, 
            prompt: str, 
            model: str = None, 
            history: str = None, 
            enable_tools: bool = True, 
            image: discord.Attachment = None, 
            text_file: discord.Attachment = None,
            is_vision_model: bool = False
        ):
        try:
            db_client = AsyncIOMotorClient(MONGO_URL)
            db = db_client['aichat_chat_history']
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
            logger.error('Error accured at agent command', exc_info=True)
        finally:
            if db_client:
                db_client.close()

async def setup(bot):
    await bot.add_cog(AIChat(bot))