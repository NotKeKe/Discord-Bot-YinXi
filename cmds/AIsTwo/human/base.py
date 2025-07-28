from discord.ext import commands
from cmds.AIsTwo.base_chat import base_zhipu_chat, base_openai_chat
from cmds.AIsTwo.others.decide import Preference, UserInfo
from cmds.AIsTwo.info import HistoryData
from cmds.AIsTwo.vector import chat_human as v_chat
from core.functions import current_time

with open('./cmds/AIsTwo/human/prompt/prompt4.md', 'r', encoding='utf-8') as f:
    base_system_prompt_4 = f.read()

processing = {} # 頻道ID
ex_processing = {
    'channelID': [] # userID
}

def chat_human(ctx: commands.Context, history: list = None):
    channelID = str(ctx.channel.id)
    userID = ctx.author.id
    if channelID in processing: processing[channelID].append(userID)
    else: processing[channelID] = [userID]

    prompt = ctx.message.content
    model = 'qwen-3-32b'
    temperature = 0.9
    top_p = 1
    # frequency_penalty = 1.3
    # presence_penalty = 1.2

    system_prompt = base_system_prompt_4
    preference = Preference.get_preferences(userID or ctx.author.id)
    info = UserInfo(userID or ctx.author.id).get_info()
    name = ctx.author.name
    collection = v_chat.create()
    ex_response = v_chat.get(collection, prompt, 5)
    ex_response = '- '.join(ex_response)
    print(f'{ex_response=}')
    system_prompt.format(preference=preference, name=name, info=info, ex_response=ex_response, time=current_time())
    delete_tools = ['current_time', 'calculate', 'image_generate', 'video_generate', 'knowledge_search', 'knowledge_save']

    try:
        if not history:
            history = HistoryData.chat_human[str(ctx.channel.id)]
    except:
        history = None
    try:
        # think, result = base_openrouter_chat(prompt, model, temperature, history, system_prompt, top_p=0.9, ctx=ctx)
        # model = 'Yinr/Tifa-qwen2-v0.1:7b'
        # model = 'openhermes:latest'
        think, result = base_openai_chat(prompt, model, temperature, history, system_prompt, top_p=top_p, ctx=ctx, is_enable_thinking=True, delete_tools=delete_tools)
    except Exception as e:
        print(f'API限制中，需要重試 (reason: {e})')
        think, result = base_zhipu_chat(prompt, 'glm-4-flash', temperature, history, system_prompt, top_p=top_p, ctx=ctx)   

    processing[channelID].remove(userID)
    if not processing[channelID]: del processing[channelID]
    return think, result

def style_train(ctx: commands.Context):
    prompt = ctx.message.content
    system_prompt = 'None' + f'\n    並且 你必須知道現在時間為{current_time()}'

    try: history = HistoryData.style_train['data']
    except: history = None

    think, result, *_ = base_zhipu_chat(prompt, 'glm-4-flash', 0.8, history, system_prompt,
                                             is_enable_tools=True)
    HistoryData.appendHistoryForStyleTrain(prompt, result, think)
    return think, result