import discord
from discord.ext import commands
from discord import app_commands

from core.functions import read_json, write_json, settings
from core.classes import Cog_Extension
from core.translator import locale_str

s_path = './Suggest_Report/suggests.json'
r_path = './Suggest_Report/reports.json'

suggest_channel = int(settings['suggest_channel'])
report_channel = int(settings['report_channel'])

class SuggestReport(Cog_Extension):
    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')

    @commands.hybrid_command(name=locale_str('suggest'), description=locale_str('suggest'))
    @app_commands.describe(建議=locale_str('suggest_suggestion'))
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
            await ctx.send(await ctx.interaction.translate('send_suggest_channel_not_found'))
            return

        try:
            await channel.create_thread(name=建議, content=f'{ctx.author.name} ({ctx.author.id}) 建議: {建議}')
            await ctx.send((await ctx.interaction.translate('send_suggest_success')).format(suggestion=建議), ephemeral=True)
        except discord.HTTPException:
            await ctx.send(await ctx.interaction.translate('send_suggest_fail'), ephemeral=True)
        except discord.Forbidden:
            await ctx.send(await ctx.interaction.translate('send_suggest_no_permission'))
        except Exception as exception:
            await ctx.invoke(self.bot.get_command('errorresponse'), 檔案名稱=__name__, 指令名稱=ctx.command.name, exception=exception, user_send=False, ephemeral=False)

    @commands.hybrid_command(name=locale_str('report'), description=locale_str('report'), aliases=['error'])
    @app_commands.describe(錯誤=locale_str('report_error'))
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
            await ctx.send(await ctx.interaction.translate('send_report_channel_not_found'))
            return

        try:
            await channel.create_thread(name=錯誤, content=f'{ctx.author.name} ({ctx.author.id}) 建議: {錯誤}')
            await ctx.send((await ctx.interaction.translate('send_report_success')).format(error=錯誤), ephemeral=True)
        except discord.HTTPException:
            await ctx.send(await ctx.interaction.translate('send_report_fail'), ephemeral=True)
        except discord.Forbidden:
            await ctx.send(await ctx.interaction.translate('send_report_no_permission'))
        except Exception as exception:
            await ctx.invoke(self.bot.get_command('errorresponse'), 檔案名稱=__name__, 指令名稱=ctx.command.name, exception=exception, user_send=False, ephemeral=False)

    @commands.command()
    async def issue_solve(self, ctx:commands.Context):
        '''
        只有克克能用的話  還需要幫助嗎:thinking:
        '''
        if not isinstance(ctx.channel, discord.Thread): await ctx.send(await ctx.interaction.translate('send_issue_solve_not_thread')); return
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

                await ctx.send(await ctx.interaction.translate('send_issue_solve_success'))
            else:
                await ctx.send(await ctx.interaction.translate('send_issue_solve_not_found'))
                
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
                    
                await ctx.send(await ctx.interaction.translate('send_issue_solve_success'))
            else:
                await ctx.send(await ctx.interaction.translate('send_issue_solve_not_found'))
        



async def setup(bot):
    await bot.add_cog(SuggestReport(bot))