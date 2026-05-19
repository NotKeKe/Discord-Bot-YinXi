from openai import OpenAI
from tenacity import retry, wait_exponential, stop_after_attempt, before_sleep_log
import os

from cmds.AIs.zhipu import ifTools_zhipu

openrouter_KEY = os.getenv('openrouter_KEY')

openrouter_moduels = [
    'deepseek/deepseek-r1:free',
    'qwen/qwq-32b:free',
    'qwen/qwen2.5-vl-72b-instruct:free',
    'google/gemini-2.0-flash-thinking-exp:free',
    'meta-llama/llama-3.3-70b-instruct:free',
    'deepseek/deepseek-chat:free',
    'deepseek/deepseek-r1-distill-llama-70b:free',
    'openchat/openchat-7b:free'
]

openrouter_moduels.sort()

default_system_chat = [
    {
        'role': 'system',
        'content': '你的名字是克克的分身，是一個由台灣高中生所製作出來的Discord Bot，而你的任務是使用輕鬆的語氣，並且一定要增加一些顏文字(如: (つ´ω`)つ)來回應使用者的訊息。' +
                '此外，你並不知道你所擁有的任何指令(因為這是由我定義的不是你)，所以不要給予使用者錯誤的引導。' +
                '如果使用者需要你寫出code的話，則需要加入註解。輸出內容要在1024個字元以內。' + 
                '而使用者如果像你提問問題的話，你必須要在解決問題後，為使用者提出至少一點建議。' + 
                '如果使用者使用繁體中文輸入，那你也必須全程以繁體中文做輸出。'
    }
]

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=openrouter_KEY,
)

def custom_before_sleep(retry_state):
    wait = retry_state.next_action.sleep
    print(f"冷卻中～請等待 {wait:.1f} 秒後重試 (第{retry_state.attempt_number}次)")

@retry(stop=stop_after_attempt(5), 
       wait=wait_exponential(multiplier=1, min=2, max=30),
       before_sleep=custom_before_sleep)
def chat_openrouter(prompt, model = None, temperature:float = None, history = None):
    try:
        if model is None: model = 'deepseek/deepseek-chat:free'
        if temperature is None: temperature = 0.7
        if history is None: history = []
        system = default_system_chat

        message = [
            {  
                'role': 'user',
                'content': prompt
            }
        ]
        messages = history + message
        try:
            messages = ifTools_zhipu(messages)
        except Exception as e: 
            print(f'Error from ifTools_zhipu {e}')

        completion = client.chat.completions.create(
            model=model,
            messages=system + messages,
            max_completion_tokens=1000,
            temperature=temperature,
        )

        result = completion.choices[0].message.content
        try:
            think = completion.choices[0].message.reasoning 
        except:
            think = None

        return think, result
    except Exception as e:
        raise(f'API限制中，需要重試 (reason: {e})')
    print(f'reason = {completion.choices[0].message.reasoning}')

def summarize(history: list):
    message = [
        {
            'role': 'system', 
            'content': '以下是一些对话记录，请对这些对话进行总结，并保留所有重要信息。请给出详细总结，但不要删除任何重要的内容' +
                        '如果對話中有包括使用者ID或者使用者名稱，都需要進行記錄'
        }
    ]
    messages = message + history
    response = client.chat.completions.create(
        model='deepseek/deepseek-r1:free',
        messages=messages,
        max_completion_tokens=4096,
        temperature=0.6
    )
    return response.choices[0].message.content