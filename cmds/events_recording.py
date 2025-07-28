import discord
from discord.ext import commands

from core.classes import Cog_Extension
from core.functions import create_basic_embed, read_json, write_json
from core.translator import locale_str

PATH = './cmds/data.json/events_record.json'

example_data = {
    'ctx.guild.id': {
        'messageChannel': 121561651,
        'roleChannel': 1215615
    }
}

def compare_list(a, b):
    '''difference1 = a比b多的，difference2 = b比a多的'''
    set1 = set(a)
    set2 = set(b)

    difference1 = []
    difference2 = []

    difference1 = set1 - set2
    difference2 = set2 - set1

    return list(difference1), list(difference2)

class Events_Recording(Cog_Extension):
    data = None

    @classmethod
    def initdata(cls):
        cls.data = read_json(PATH)

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')
        self.__class__.initdata()

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        guild = before.guild
        guildID = str(guild.id)
        data = self.__class__.data

        if data is not None and data == {}: return
        if guildID not in data: return
        if 'messageChannel' not in data[guildID]: return

        sended_channel = await self.bot.fetch_channel(data[guildID]['messageChannel'])

        member = before.author
        channel = before.channel
        embed = create_basic_embed(color=discord.Color.light_gray)
        embed.set_author(name=member.global_name, icon_url=member.avatar_url)
        embed.add_field(name=await self.bot.tree.translator.translate(locale_str('embed_events_recording_message_edit_before'), sended_channel.guild.preferred_locale, None), value=f'```{before.content}```', inline=False)
        embed.add_field(name=await self.bot.tree.translator.translate(locale_str('embed_events_recording_message_edit_after'), sended_channel.guild.preferred_locale, None), value=f'```{after.content}```', inline=False)
        embed.set_footer(text=channel.name)
        await sended_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message:discord.Message):
        guild = message.guild
        if not guild: return
        guildID = str(guild.id)
        data = self.__class__.data

        if data is not None and data == {}: return
        if guildID not in data: return
        if 'messageChannel' not in data[guildID]: return

        sended_channel = await self.bot.fetch_channel(data[guildID]['messageChannel'])

        user = message.author
        channel = message.channel
        embed = create_basic_embed(color=discord.Color.light_gray)
        embed.set_author(name=user.global_name, icon_url=user.avatar_url)
        embed.add_field(name=await self.bot.tree.translator.translate(locale_str('embed_events_recording_message_delete'), sended_channel.guild.preferred_locale, None), value=f'```{message.content}```', inline=False)
        embed.set_footer(text=channel.name)
        await sended_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        guild = role.guild
        guildID = str(guild.id)
        data = self.__class__.data

        if guildID not in data: return
        if 'roleChannel' not in data[guildID]: return

        sended_channel = await self.bot.fetch_channel(data[guildID]['roleChannel'])
        
        embed = create_basic_embed(color=discord.Color.light_gray)
        embed.set_author(name=guild.name, icon_url=guild.icon_url)
        embed.add_field(name=await self.bot.tree.translator.translate(locale_str('embed_events_recording_role_create'), sended_channel.guild.preferred_locale, None), value=f'```{role.name}```', inline=True)

        await sended_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        pass



        




async def setup(bot):
    await bot.add_cog(Events_Recording(bot))