import discord
from discord import app_commands
from discord.ext import commands
import qrcode
import os

from core.classes import Cog_Extension
from core.functions import create_basic_embed

class QRcodeGenerator(Cog_Extension):
    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')

    def qrcode_gen(self, url:str):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4
        )
        qr.add_data(url)   # 要轉換成 QRCode 的文字
        qr.make(fit=True)          # 根據參數製作為 QRCode 物件

        img = qr.make_image()      # 產生 QRCode 圖片
        img.save('qrcode.png')     # 儲存圖片

    @commands.hybrid_command(aliases=['qr', 'QR', 'qrcode'], name='qrcode生成器', description='Generate a QRcode')
    @app_commands.describe(url='在此輸入連結')
    async def img(self, ctx, * , url:str):
        async with ctx.typing():
            try:
                self.qrcode_gen(url)
            except:
                await ctx.send('該功能目前無法使用 或你的連結有問題，請稍後再試')

            file = discord.File('qrcode.png')
            os.remove('qrcode.png')

            embed = create_basic_embed(title=url, color=ctx.author.color, 功能='QRcode生成器', time=False)
            embed.set_image(url="attachment://qrcode.png")
            embed.set_footer(text='Python module "qrcode"')

            await ctx.send(file=file, embed=embed)

async def setup(bot):
    await bot.add_cog(QRcodeGenerator(bot))