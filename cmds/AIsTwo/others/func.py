from cmds.AIsTwo.base_chat import true_zhipu, base_zhipu_chat, openrouter, true_ollama, base_openai_chat
from cmds.AIsTwo.utils import image_url_to_base64, image_size, on_timeout, to_system_message, to_user_message
from datetime import datetime
import time

def image_generate(prompt: str):
    '''return image URL and time passed'''
    response = true_zhipu.images.generations(
        model="cogview-3-flash",
        prompt=prompt,
    )

    time = datetime.now() - datetime.fromtimestamp(response.created)

    return response.data[0].url, time.total_seconds()

def video_generate(prompt: str, image_url = None, size=None, fps=60, with_audio: bool=True, duration: int=5):
    imageBase64 = None
    if image_url is not None:
        imageBase64 = image_url_to_base64(image_url)
        if size is None:
            size = image_size(imageBase64)

    if size is None:
        size = '1920x1080'

    response = true_zhipu.videos.generations(
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
            response2 = true_zhipu.videos.retrieve_videos_result(
                    id=id
                )
            if response2.task_status == 'SUCCESS':
                return response2.video_result[0].url
            elif response2.task_status == 'FAIL':
                return '生成失敗'
            
            if on_timeout(rn):
                return 'Timeout (時間超過20分鐘)'
        except: return 'API發送失敗'

def gener_title(prompt: str):
    '''Generate title by glm-4-flash'''
    model = 'glm-4-flash'
    system_prompt = ('以下是AI(assistant)與使用者(user)的對話，請你為他們的對話做一個約15字的標題。' +
                    '輸出結果不能包括標點符號及換行符，如需使用標點符號請以" "(即空格符號)作為代替。' +
                    '輸出格式: {標題}')

    result = base_zhipu_chat(prompt, model, 0.5, system_prompt=system_prompt)
    return result 

def summarize(history: list, system_prompt: str = None):
    if not system_prompt:
        message = to_system_message('''
                你是一個AI助手，你的任務是幫助使用者總結對話內容。
                你會根據對話內容進行詳細的總結。
                輸出結果將會在1000字內
                如果對話內容中包含使用者ID或者使用者名稱，則都一定要記錄下來。
                而在總結當中，你認為重要的地方，也一定要使用markdown語法來加粗。
                **使用`絕對客觀`的方式進行總結，不要對對話做出任何評價。**
                **不要總結出影響AI之後對話的內容**
                ''')
    else: message = to_system_message(system_prompt)
    messages = message + history

    response = openrouter.chat.completions.create(
        model='deepseek/deepseek-r1-0528:free',
        messages=messages,
        max_completion_tokens=4096,
        temperature=0.6
    )
    return response.choices[0].message.content

def translate(prompt: str, to_lang: str = '英文'):
    system_prompt = '''
            你的名字是克克的分身，是一個由台灣高中生所製作出來的Discord Bot，而你的任務是幫助使用者翻譯句子或者是單詞，而語言會由使用者決定。
            輸出內容要在1024個字元以內。
            輸出格式如下: 
                    來源語言: {source_language} \n 目標語言: {target_language} \n
                    原文: {使用者輸入} \n **翻譯後: {翻譯結果}** \n
                    其他可能的結果: {other_results} \n
            注意事項:
                    1. 其他可能的結果必須以列點式呈現，並且每一個結果都必須以「-」開頭。
            '''

    prompt = f'請你幫我把`{prompt}`翻譯成`{to_lang}`'

    # think, result = base_zhipu_chat(prompt, 'glm-4-flash', 0.7, system_prompt=system_prompt, is_enable_tools=False)
    think, result = base_openai_chat(prompt, 'qwen-3-32b', system_prompt=system_prompt, is_enable_tools=False, is_enable_thinking=False, no_extra_system_prompt=True)
        
    return think, result

def image_read(prompt: str, image_url: str) -> str:
    try:
        messages = [
            {
                'role': 'user',
                'content': [
                    {
                        'type': 'text',
                        'text': prompt
                    },
                    {
                        'type': 'image_url',
                        'image_url': {
                            'url': image_url
                        }
                    }
                ]
            }
        ]

        response = true_zhipu.chat.completions.create(
            model='glm-4v-flash',
            messages=messages,
            temperature=0.7,
            max_tokens=1000,
        )

        return response.choices[0].message.content
    except Exception as e1: 
        return '圖片無法判讀' + str(e1)