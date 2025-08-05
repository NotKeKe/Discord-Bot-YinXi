from discord import Interaction, ButtonStyle, Message
from discord.ui import View, Button

async def add_think_button(msg: Message, view: View, think: str):
    if think:
        async def button_callback(interaction: Interaction):
            await interaction.response.edit_message(view=view)
            await interaction.followup.send(think, ephemeral=True)
        
        button = Button(label='想法', style=ButtonStyle.blurple)                
        button.callback = button_callback
        view.add_item(button)

        msg = await msg.edit(view=view)
        timeout = await view.wait()
        if timeout: await msg.edit(view=None)