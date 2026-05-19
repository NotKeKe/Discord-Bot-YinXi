import os
from dotenv import load_dotenv
from zhipuai import ZhipuAI
from zhipuai.core._errors import APIRequestFailedError, APIStatusError
from datetime import datetime
import time
import requests
import base64
import orjson
from PIL import Image
from io import BytesIO

from core.functions import read_json, current_time

default_system_chat = [
    {
        'role': 'system',
        'content': '你的名字是克克的分身，是一個由台灣高中生所製作出來的Discord Bot，而你的任務是使用輕鬆的語氣，並且一定要增加一些顏文字(如: (つ´ω`)つ)來回應使用者的訊息。'+
                '如果使用者需要你寫出code的話，則需要加入註解。輸出內容要在1024個字元以內。' + 
                '而使用者如果像你提問問題的話，你必須要在解決問題後，為使用者提出至少一點建議。' + 
                '如果提供了使用者ID，則在對話內容中僅使用相同使用者ID的前後文。' + 
                '每次對話的使用者可能都會不一樣。' +
                '如果使用者使用繁體中文輸入，那你也必須全程以繁體中文做輸出。'
    }
]

load_dotenv()
API_KEY = os.getenv('zhipuAI_KEY')

client = ZhipuAI(
    api_key=API_KEY
)

def image_size(image_base64) -> str:
    image_data = base64.b64decode(image_base64)
    image = Image.open(BytesIO(image_data))

    # 获取圖片大小
    width, height = image.size
    return f'{width}x{height}'

def image_url_to_base64(image_url):
    response = requests.get(image_url)
    if response.status_code == 200:
        base64_string = base64.b64encode(response.content).decode('utf-8')
        return base64_string
    else:
        return None

def on_timeout(time):
    t = datetime.now() - datetime.fromtimestamp(timestamp=time)
    if t.total_seconds() > 1200:
        return True
    
def gener_title(input):
    message = [
        {
            'role': 'system', 
            'content': '以下是AI(assistant)與使用者(user)的對話，請你為他們的對話做一個約15字的標題。' +
                '輸出結果不能包括標點符號及換行符，如需使用標點符號請以" "(即空格符號)作為代替。' +
                '輸出格式: {標題}'
        }
    ]

    messages = message + input
    response = client.chat.completions.create(
        model='glm-4-flash',
        messages=messages,
        temperature=0.5,
        max_tokens=20
    )
    return response.choices[0].message.content
    
# 對話紀錄總結(荒廢)
def summarize(history: list):
    message = [
        {'role': 'system', 
         'content': '以下是一些对话记录，请对这些对话进行总结，并保留所有重要信息。请给出详细总结，但不要删除任何重要的内容' +
                '如果對話中有包括使用者ID或者使用者名稱，都需要進行記錄'
        }
    ]
    messages = message + history
    response = client.chat.completions.create(
        model='glm-4-flash',
        messages=messages,
        temperature=0.9,
        max_tokens=500
    )
    return response.choices[0].message.content

def image_read(require: str, image_url: str) -> str:
    messages = [
        {
            'role': 'user',
            'content': [
                {
                    'type': 'text',
                    'text': require
                },
                {
                    'type': image_url,
                    'image_url': {
                        'url': image_url
                    }
                }
            ]
        }
    ]

    response = client.chat.completions.create(
        model='glm-4v-flash',
        messages=messages,
        temperature=0.6
    )

    return response.choices[0].message.content

def video_read(require: str, video_url: str) -> str:
    messages = [
        {
            'role': 'user',
            'content': [
                {
                    'type': 'text',
                    'text': require
                },
                {
                    'type': video_url,
                    'video_url': {
                        'url': video_url
                    }
                }
            ]
        }
    ]

    response = client.chat.completions.create(
        model='glm-4v-flash',
        messages=messages,
        temperature=0.6
    )

    return response.choices[0].message.content

def code_response(messages: str, history: list = None) -> str:
    '''
    messages: 使用者此次輸入內容
    history: 使用者的聊天紀錄: list
    '''
    message = [
        {
            'role': 'system',
            'content': '你是一位對python以及各大程式語言有深入了解的程序員，你現在需要為使用者查詢最新結果，並輸出清晰且附帶註釋的代碼'
        }
    ]
    
    if history is not None:
        message += history

    message.append({'role': 'user', 'content': messages})
        
    response = client.chat.completions.create(
        model='glm-4-alltools',
        messages=message,
        stream=True,
        temperature=0.6,
        max_tokens=900,
        tools=[
            {
                "type": "web_browser",
                "web_browser":{
                    "browser" :"auto"
                }
            },
            {
                "type": "code_interpreter"
            }
        ]
    )

    lst = [trunk.choices[0].delta.content for trunk in response if trunk.choices[0].delta.content is not None]
    # print(len(lst))
    result = ''.join(lst)
    return result

# 判斷是否需要使用工具
def ifTools_zhipu(messages: list):
    from cmds.AIs.tool_funcs import func_map
    from cmds.AIs.info import tools_descrip
    
    response = client.chat.completions.create(
        model="glm-4-flash",  # 请填写您要调用的模型名称
        messages=messages,
        tool_choice='auto',
        tools=tools_descrip
    )

    if response.choices[0] is None: raise '沒有回應'

    # 不需要tools則跳出while迴圈並return
    if response.choices[0].message.tool_calls is None: return messages

    # tools結果
    result = []
    is_curretTime = False
    for tool_call in response.choices[0].message.tool_calls:
        tool_name = tool_call.function.name
        args = orjson.loads(tool_call.function.arguments)
        print(args)
        result.append(f'{tool_name}: {func_map[tool_name](**args)}')

        if tool_name == 'current_time': is_curretTime = True
    
    if not is_curretTime:
        result.append(f'現在時間為: {current_time()}')

    func_results:str = '\n\n\n'.join(result)
    messages += [
        {
            'role': 'user',
            'content': f'tool輸出為: {func_results}'
        }
    ]
    return messages  

def search(user_input: str) -> str:
    '''with glm 4 alltools'''
    response = client.chat.completions.create(
        model="glm-4-alltools",
        stream=True,
        max_tokens=1000,
        messages=[
            {
                "role": "user",
                "content":[
                    {
                        "type":"text",
                        "text": user_input
                    }
                ]
            }
        ],
        tools=[
            {
                "type": "web_browser",
                "web_browser":{
                    "browser" :"auto"
                }
            },
        ]
    )

    lst = [trunk.choices[0].delta.content for trunk in response if trunk.choices[0].delta.content is not None]
    # print(len(lst))
    result = ''.join(lst)
    return result


def response(content: str, history= None) -> str:
    '''
    content: 使用者此次輸入內容
    require: 使用者的需求
    history: 使用者的聊天紀錄: list
    '''
    messages = []

    if history is not None:
        messages += history

    messages.append({'role': 'user', 'content': content})

    messages = ifTools_zhipu(messages)
        
    response = client.chat.completions.create(
        model='glm-4-plus',
        messages=default_system_chat + messages,
        temperature=0.6,
        max_tokens=1000,
        tool_choice='auto'
    )
    return response.choices[0].message.content

def image_generate(prompt: str):
    '''return image URL and time passed'''
    response = client.images.generations(
        model="cogview-3-flash",
        prompt=prompt,
    )

    time = datetime.now() - datetime.fromtimestamp(response.created)

    return response.data[0].url, time.total_seconds()

def video_generate(prompt: str, image_url = None, size=None, fps=60, with_audio: bool=True, duration: int=5):
    if image_url is not None:
        imageBase64 = image_url_to_base64(image_url)
        if size is None:
            size = image_size(imageBase64)

    if size is None:
        size = '1920x1080'

    response = client.videos.generations(
        model="cogvideox-flash",
        image_url=imageBase64,
        prompt=prompt,  
        quality="quality",
        with_audio=with_audio,
        size=size,
        duration=duration,
        fps=fps,
    )

    id = response.id
    print(f'{id}: {prompt}')
    rn = time.time()

    while True:
        time.sleep(10)
        try:
            response2 = client.videos.retrieve_videos_result(
                    id=id
                )
            if response2.task_status == 'SUCCESS':
                return response2.video_result[0].url
            elif response2.task_status == 'FAIL':
                return '生成失敗'
            
            if on_timeout(rn):
                return 'Timeout (時間超過20分鐘)'
        except: return 'API發送失敗'

def translate(messages: str, to_lang: str = '英文', require: str = None) -> str:
    message = [
        {'role': 'system', 
         'content': '你的名字是克克的分身，是一個由台灣高中生所製作出來的Discord Bot，而你的任務是幫助使用者翻譯句子或者是單詞，而語言會由使用者決定。' +
         '輸出內容要在1024個字元以內。輸出格式如下: 「來源語言: {來源語言} {換行符} 目標語言: {目標語言} {換行符} ' + 
         '原文: {使用者輸入} {換行符} **翻譯後: {翻譯結果}**」'
        }
    ]

    content = f'請你幫我把{messages}翻譯成{to_lang}'

    if require is not None:
        message.append({'role': 'system', 'content': require})
        message.append({'role': 'user', 'content': content})
    else:
        message.append({'role': 'user', 'content': content})
        
    response = client.chat.completions.create(
        model='glm-4-flash',
        messages=message,
        
    )
    return response.choices[0].message.content

def test():
    response = client.chat.completions.create(
        model="emohaa",  # 填写需要调用的模型名称
        meta={
            "user_info": "30岁的男性软件工程师，兴趣包括阅读、徒步和编程",
            "bot_info": "Emohaa是一款基于Hill助人理论的情感支持AI，拥有专业的心理咨询话术能力",
            "bot_name": "Emohaa",
            "user_name": "张三"
        },
        messages=[
            {
                "role": "user",
                "content": "你好，我是克，你可以介紹一下你自己嗎。"
            },
        ]
    )

    return response.choices[0].message.content

if __name__ == '__main__':
    lst = [
         {
            "role": "user",
            "content": "703877871256731678: 「使用者ID: 703877871256731678，使用者名稱: 克克 KeJC」說了嗨"
        },
        {
            "role": "assistant",
            "content": "嗨～克克 KeJC！歡迎來到我的頻道～ (つ´ω`)つ 有什麼我可以幫助你的嗎？"
        },
        {
            "role": "user",
            "content": "703877871256731678: 「使用者ID: 703877871256731678，使用者名稱: 克克 KeJC」說了: `你可以自我介紹嗎`"
        },
        {
            "role": "assistant",
            "content": "當然可以呀，克克 KeJC！我是克克的分身，一個由台灣高中生製作的Discord Bot。我會盡力用輕鬆的語氣陪伴大家，回答問題，還可以幫忙寫程式呢！(つ´ω`)つ 如果你有什麼問題或需要幫助，隨時可以找我哦～"
        },
        {
            "role": "user",
            "content": "703877871256731678: 「使用者ID: 703877871256731678，使用者名稱: 克克 KeJC」說了: `你認識羽幻嗎`"
        },
    ]
    aa = summarize(lst)
    print(aa)


