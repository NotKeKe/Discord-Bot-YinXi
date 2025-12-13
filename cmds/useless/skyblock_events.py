import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import asyncio

from cmds.skyblock_commands_foldor import skyblock_events
from core.classes import Cog_Extension

def get_dict() -> dict:
    events = skyblock_events.show_next_events()
    return events


class skyblockEvents(Cog_Extension):

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def start_events(self, ctx): # started embed
        '''
        [start_events
        開始取得skyblock的活動
        '''
        
        # if isinstance(ctx.channel, discord.DMChannel):
        #     await ctx.send("我不在私訊中處理這項指令")
        #     return
        
        events = get_dict()

        embed=discord.Embed(title="Events", color=discord.Color.blue(), timestamp=datetime.now())
        embed.set_author(name="取得skyblock活動")
        for event in events:
            embed.add_field(name=event, value=f"開始時間: {events[event]['Start']}\n結束時間: {events[event]['End']}", inline=False)

            
        await ctx.send(embed=embed)

        
        


        

    @tasks.loop(hours=24)  # 每 24 小時執行一次
    async def update_embed_task(self):
        await self.wait_until_midnight()
        
        

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def stop_events(self, ctx):
        '''
        [start_events
        停止取得skyblock的活動
        '''
        await ctx.send("已停止更新 Mayor 訊息")


    @update_embed_task.before_loop
    async def before_update_embed_task(self):
        await self.bot.wait_until_ready()

    async def wait_until_midnight(self):
        now = datetime.now()
        target = datetime.combine(now + timedelta(days=1), datetime.min.time())
        wait_seconds = (target - now).total_seconds()
        await asyncio.sleep(wait_seconds)

async def setup(bot):
    await bot.add_cog(skyblockEvents(bot))