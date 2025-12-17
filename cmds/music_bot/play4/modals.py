from discord import Interaction
from discord.ui import Modal, TextInput, Label
from discord.ext import commands
import asyncio

from .utils import leave

sleeping_tasks: list[asyncio.Task] = []

async def sleep_task(ctx: commands.Context, inter: Interaction, sleep_time: int):
    """...

    Args:
        ctx (commands.Context): original context
        inter (Interaction): The interaction created by current user
        sleep_time (int): in minutes
    """    
    await asyncio.sleep(sleep_time * 60)
    try:
        await leave(ctx)
        await ctx.send(f"The music has stopped by sleep timer (created by {inter.user.global_name})")
    except: ...

class SleepTimerModal(Modal, title="睡眠計時器"):
    def __init__(self, ctx: commands.Context):
        super().__init__()
        self.ctx = ctx

    sleep_time = Label(text="Sleep Time", component=TextInput(placeholder="Enter sleep time in minutes. (e.g. 60)", required=True))

    async def on_submit(self, inter: Interaction):
        try:
            self.sleep_time = int(self.sleep_time.component.value) # type: ignore
        except:
            await inter.response.send_message("Please enter a valid number", ephemeral=True)
            return

        sleeping_tasks.append(asyncio.create_task(sleep_task(self.ctx, inter, self.sleep_time)))

        await inter.response.send_message(f"The music will stop after {self.sleep_time} minutes", ephemeral=True)