import discord
from discord.ext import commands

from core.functions import read_json, write_json, settings
from core.classes import Cog_Extension

s_path = './Suggest_Report/suggests.json'
r_path = './Suggest_Report/reports.json'

suggest_channel = int(settings['suggest_channel'])
report_channel = int(settings['report_channel'])

class SuggestReport(Cog_Extension):
    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')

    @commands.hybrid_command(aliases=['suggest'], name='建議', description='Send some suggests to me!')
    async def suggest(self, ctx:commands.Context, * , 建議: str):
        '''
        [建議 建議(輸入文字) 或是 [suggest 建議(輸入文字)
        回報給我你的建議
        我會在自己的群創建一個討論串
        '''
        data = read_json(s_path)
        data[建議] = ctx.author.id
        write_json(data, s_path)

        channel = await self.bot.fetch_channel(suggest_channel)
        if channel is None:
            await ctx.send("Channel not found.")
            return

        try:
            await channel.create_thread(name=建議, content=f'{ctx.author.name} ({ctx.author.id}) 建議: {建議}')
            await ctx.send(f"已成功發送 「{建議}」", ephemeral=True)
        except discord.HTTPException:
            await ctx.send("目前無法建議", ephemeral=True)
        except discord.Forbidden:
            await ctx.send("I don't have permission to create threads in this channel.")
        except Exception as exception:
            await ctx.invoke(self.bot.get_command('errorresponse'), 檔案名稱=__name__, 指令名稱=ctx.command.name, exception=exception, user_send=False, ephemeral=False)

    @commands.hybrid_command(aliases=['report', 'error'], name='錯誤回報', description='Report some errors to me!')
    async def report(self, ctx:commands.Context, * , 錯誤: str):
        '''
        [錯誤回報 錯誤(輸入文字) 或是 [report 建議(輸入文字) 或是 [error 建議(輸入文字)
        回報錯誤給我
        我會在自己的群創建一個討論串
        '''
        data = read_json(r_path)
        data[錯誤] = ctx.author.id
        write_json(data, r_path)

        channel = await self.bot.fetch_channel(report_channel)
        if channel is None:
            await ctx.send("Channel not found.")
            return

        try:
            await channel.create_thread(name=錯誤, content=f'{ctx.author.name} ({ctx.author.id}) 建議: {錯誤}')
            await ctx.send(f"問題「{錯誤}」 已成功回報錯誤", ephemeral=True)
        except discord.HTTPException:
            await ctx.send("目前回報錯誤", ephemeral=True)
        except discord.Forbidden:
            await ctx.send("I don't have permission to create threads in this channel.")
        except Exception as exception:
            await ctx.invoke(self.bot.get_command('errorresponse'), 檔案名稱=__name__, 指令名稱=ctx.command.name, exception=exception, user_send=False, ephemeral=False)

    @commands.command()
    async def issue_solve(self, ctx:commands.Context):
        '''
        只有克克能用的話  還需要幫助嗎:thinking:
        '''
        if not isinstance(ctx.channel, discord.Thread): await ctx.send('這不是Thread啊 你在幹嘛'); return
        if ctx.channel.parent.name == '建議':
            data = read_json(s_path)

            if str(ctx.channel.name) in data:
                del data[str(ctx.channel.name)]
                write_json(data, s_path)
                await ctx.channel.edit(name=str(ctx.channel.name)+' SOLVE')

                # if isinstance(ctx.channel, discord.Thread): 
                #     await ctx.channel.delete() 
                # else: 
                #     await ctx.send("This is not a thread.")
                #     return

                await ctx.send("Issue Solve")
            else:
                await ctx.send('事件不存在')
                
        elif ctx.channel.parent.name == '錯誤回報':
            data = read_json(r_path)

            if str(ctx.channel.name) in data:
                del data[str(ctx.channel.name)]
                write_json(data, r_path)
                await ctx.channel.edit(name=str(ctx.channel.name)+' SOLVE')

                # if isinstance(ctx.channel, discord.Thread): 
                #     await ctx.channel.edit(archived)
                # else: 
                #     await ctx.send("This is not a thread.")
                #     return
                    
                await ctx.send("Issue Solve")
            else:
                await ctx.send('事件不存在')
        



async def setup(bot):
    await bot.add_cog(SuggestReport(bot))