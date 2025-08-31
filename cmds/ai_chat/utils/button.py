from discord import Interaction, ButtonStyle, Message, File
from discord.ui import View, Button
import io
import orjson

async def add_think_button(msg: Message, view: View, think: str):
    if think:
        async def button_callback(interaction: Interaction):
            if len(think) >= 1999:
                bytes_io = io.BytesIO(think.encode())
                file = File(bytes_io, filename='think.txt')
                await interaction.response.send_message(file=file, ephemeral=True)
            else:
                await interaction.response.send_message(think, ephemeral=True)
        
        button = Button(label='想法', style=ButtonStyle.blurple)                
        button.callback = button_callback
        view.add_item(button)

        msg = await msg.edit(view=view)

async def add_history_button(msg: Message, view: View, history: list):
    bytes_io = io.BytesIO(orjson.dumps(history, option=orjson.OPT_INDENT_2))
    f = File(bytes_io, filename='history.json')

    async def button_callback(interaction: Interaction):
        await interaction.response.send_message(file=f, ephemeral=True)

    button = Button(label='歷史紀錄', style=ButtonStyle.blurple)
    button.callback = button_callback
    view.add_item(button)

    msg = await msg.edit(view=view)