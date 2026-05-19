import os
import typing
import traceback
import discord
from discord import app_commands
from discord.ext import commands

from core.functions import read_json, write_json
from core.functions import create_basic_embed
from cmds.AIs.zhipu import gener_title

HISTORY_DATA_PATH = './cmds/data.json/chat_history.json'
HISTORY_DATA_FORCHANNEL_PATH = './cmds/data.json/chat_history_forchannel.json'
channel_model_select_PATH = './cmds/data.json/chat_channel_modelSelect.json'

tools_description_json_PATH = './cmds/AIs/datas/tools_descrip.json'
tools_descrip = read_json(tools_description_json_PATH)['tools']

available_modules = [
    {
        'module': 'deepseek-ai/DeepSeek-R1',
        'provider': 'novita'
    },
    {
        'module': 'deepseek-ai/DeepSeek-V3',
        'provider': 'novita'
    }
]

HUGGINGKEY = os.getenv('huggingFace_KEY')

class HistoryData:
    user = None
    channel = None
    channel_model_select = None

    @classmethod
    def initdata(cls):
        if cls.user is None:
            cls.user = read_json(HISTORY_DATA_PATH)
        if cls.channel is None:
            cls.channel = read_json(HISTORY_DATA_FORCHANNEL_PATH)
        if cls.channel_model_select is None:
            cls.channel_model_select = read_json(channel_model_select_PATH)
    
    @classmethod
    def writeUser(cls, data=None):
        if data is not None:
            cls.user = data

        write_json(cls.user, HISTORY_DATA_PATH)

    @classmethod
    def writeChannel(cls, data=None):
        if data is not None:
            cls.channel = data

        write_json(cls.channel, HISTORY_DATA_FORCHANNEL_PATH)

    @classmethod
    def writeChannelSelectModel(cls, ctx: commands.Context, model: str = None):
        if model is not None:
            cls.channel_model_select[str(ctx.channel.id)] = model
            
        write_json(cls.channel_model_select, channel_model_select_PATH)

    @classmethod
    def createNewHistory(cls, userID, content, result):
        userID = str(userID)
        data = cls.user

        results = [
            {
                'role': 'user',
                'content': content
            },
            {
                'role': 'assistant', 
                'content': result
            }
        ]

        # title = content if len(content) < 20 else content[:20]
        title = gener_title(results) if len(content) >= 20 else content

        if userID not in data:
            data[userID] = {
                title: results
            }
        else:
            data[userID][title] = results

        cls.writeUser(data)

    @classmethod
    def appendHistory(cls, userID, content, result, title=None):
        userID = str(userID)
        data = cls.user

        if title is None or userID not in data:
            cls.createNewHistory(userID, content, result); return
    
        data[userID][title] += (
            {
                'role': 'user',
                'content': content
            },
            {
                'role': 'assistant', 
                'content': result
            }
        )

        cls.writeUser(data)

    @classmethod
    def appendHistoryForChannel(cls, channelID, content, result):
        channelID = str(channelID)

        data = cls.channel

        data[channelID] += (
            {
                'role': 'user',
                'content': content,
            },
            {
                'role': 'assistant', 
                'content': result
            }
        )
        cls.writeChannel(data)


async def chat_autocomplete(interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
    HistoryData.initdata()
    userID = str(interaction.user.id)

    files = list(HistoryData.user[userID])
    if current:
        files = [history for history in files if current.lower().strip() in history.lower() and history != '']

    # 限制最多回傳 25 個結果
    return [app_commands.Choice(name=history, value=history) for history in files[:25] if history != '']

def create_result_embed(ctx: commands.Context, result, model):
    embed = create_basic_embed(title='AI文字生成', color=ctx.author.color)
    embed.add_field(name=' ', value=result)
    embed.set_footer(text=f'Powered by {model}')
    return embed

def get_history(ctx: commands.Context, history_title: str = None):
    if history_title is not None:
        history = HistoryData.user[str(ctx.author.id)][history_title]
    else:
        history = None

    return history