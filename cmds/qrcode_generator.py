import discord
from discord import app_commands
from discord.ext import commands
import qrcode
import os

from core.classes import Cog_Extension
from core.functions import create_basic_embed
from core.translator import load_translated, locale_str

class QRcodeGenerator(Cog_Extension):
    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')

    def qrcode_gen(self, url:str, user_id: str):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4
        )
        qr.add_data(url)   # 要轉換成 QRCode 的文字
        qr.make(fit=True)          # 根據參數製作為 QRCode 物件

        img = qr.make_image()      # 產生 QRCode 圖片
        img.save(f'./data/temp/qrcode_{user_id}.png')     # 儲存圖片

    @commands.hybrid_command(aliases=['qr', 'QR', 'qrcode'], name=locale_str('qrcode_generator'), description=locale_str('qrcode_generator'))
    @app_commands.describe(url=locale_str('qrcode_generator_url'))
    async def img(self, ctx: commands.Context, * , url:str):
        async with ctx.typing():
            '''i18n'''
            invalid_url = await ctx.interaction.translate('send_qrcode_generator_invalid_url')
            eb = await ctx.interaction.translate('embed_qrcode_generator_1')
            eb: dict = (load_translated(eb))[0]
            author = eb.get('author')
            ''''''

            try:
                self.qrcode_gen(url, str(ctx.author.id))
            except:
                return await ctx.send(invalid_url)

            file = discord.File(f'./data/temp/qrcode_{str(ctx.author.id)}.png', 'qrcode.png')
            os.remove(f'./data/temp/qrcode_{str(ctx.author.id)}.png')

            embed = create_basic_embed(title=url, color=ctx.author.color, 功能=author, time=False)
            embed.set_image(url="attachment://qrcode.png")
            embed.set_footer(text='Python module "qrcode"')

            await ctx.send(file=file, embed=embed)

async def setup(bot):
    await bot.add_cog(QRcodeGenerator(bot))