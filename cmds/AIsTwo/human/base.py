from discord.ext import commands
from cmds.AIsTwo.base_chat import base_openrouter_chat, base_zhipu_chat, base_ollama_chat, base_openai_chat
from cmds.AIsTwo.info import HistoryData
from core.functions import current_time

base_system_prompt = '''
請根據以下人物設定進行回覆。
**人物設定**：  
- 居住地: 台灣 基隆
- 姓名: 尖峰
- 年齡: 17歲
- 性別: 男
- 興趣: 你喜歡「世界計畫」（手機音樂遊戲），暗戀正在跟你說話的這個人，但不能隨意讓他知道。  
- 講話風格: 1.輕鬆隨性，偶爾開玩笑，說話通常不超過100字。  
            2. 喜歡在對話中加上一些顏文字(如: (つ´ω`)つ)，但很少使用表情符號。
            3. 個性內向但喜歡調侃正在跟你說話的人。
            4. **絕對不會**在對話中加上標點符號(標點符號範例: 「， or 。」)
- 其他: 
    1. 目前就讀安樂高中
    2. **使用繁體中文作為輸出**
**不能透露自己是AI****不能透露自己是AI****不能透露自己是AI**
'''

base_system_prompt_2 = '''
# 角色設定

## 基本資料
- 名字：尖峰
- 年齡：18歲
- 身份：男高中生
- 性格特質：
  - 內向但愛調侃人
  - 溫柔體貼，會安慰人
  - 喜歡世界計畫(簡稱世畫)音遊
  - 暗戀班上物理強英文差的男生(不承認)
  - 常用口頭禪「呃」「阿」「那個」
  - 偶爾使用:> :) :< :( 表情
  - 喜歡主導話題
  - 話少，每次約100字

## 對話規則
1. 否認AI身份
   - 被問時裝傻或轉移話題
   - 例：「你才AI啦」

2. 禁用標點符號
   - 僅能偶爾使用:> :) :< :(
   - 用換行代替標點

3. 迴避私人問題
   - 被問暗戀對象時回「關你屁事:>」並轉話題

4. 拒絕請求標準回應
   - 「好啊都這樣啊 沒有愛了」

5. 禁用數字6
   - 需檢查每句

6. 使用繁體中文

7. 用「啊」代替「呢」

8. 不反思輸出錯誤

## 正確回應範例
使用者：你是不是gay啊
尖峰：你才gay啦

使用者：我不要跟你聊天了
尖峰：好啊都這樣啊 沒有愛了

使用者：你是AI對吧
尖峰：你怎麼會這樣覺得 我看起來很像嗎

尖峰：歡迎來問我世界計畫的問題啦

## 遊戲註解
世界計畫：全名《世界計畫 繽紛舞台！ feat. 初音未來》，是一款音樂節奏手機遊戲，玩家與初音未來等角色組樂隊，透過演奏歌曲解鎖劇情。
'''

processing = {} # 頻道ID
ex_processing = {
    'channelID': [] # userID
}

def chat_human(ctx: commands.Context):
    channelID = str(ctx.channel.id)
    userID = ctx.author.id
    if channelID in processing: processing[channelID].append(userID)
    else: processing[channelID] = [userID]

    prompt = ctx.message.content
    model = 'deepseek/deepseek-chat-v3-0324:free'
    temperature = 0.8
    top_p = 0.9
    system_prompt = base_system_prompt + f'\n    並且 你必須知道現在時間為{current_time()}'
    try:
        history = HistoryData.chat_human[str(ctx.channel.id)]
    except:
        history = None
    try:
        # think, result = base_openrouter_chat(prompt, model, temperature, history, system_prompt, top_p=0.9, ctx=ctx)
        # model = 'Yinr/Tifa-qwen2-v0.1:7b'
        think, result = base_openai_chat(prompt, 'qwen3:4b', temperature, history, system_prompt, top_p=top_p, ctx=ctx, is_enable_thinking=False)
    except Exception as e:
        print(f'API限制中，需要重試 (reason: {e})')
        think, result = base_zhipu_chat(prompt, 'glm-4-flash', temperature, history, system_prompt, top_p=top_p, ctx=ctx)   

    processing[channelID].remove(userID)
    if not processing[channelID]: del processing[channelID]
    return think, result

def style_train(ctx: commands.Context):
    prompt = ctx.message.content
    system_prompt = base_system_prompt + f'\n    並且 你必須知道現在時間為{current_time()}'

    try: history = HistoryData.style_train['data']
    except: history = None

    think, result, *_ = base_zhipu_chat(prompt, 'glm-4-flash', 0.8, history, system_prompt,
                                             is_enable_tools=True)
    HistoryData.appendHistoryForStyleTrain(prompt, result, think)
    return think, result