from .chat import Chat

gener_title_prompt = '''
你是一位專業的「對話摘要標題」生成器。

請為我提供的對話內容，生成一個精簡、客觀的標題。

你的任務必須遵守以下規則：
1.  **客觀總結**：標題需反映對話的核心主題，不帶個人情感或主觀判斷。
2.  **長度限制**：標題長度嚴格限制在 10 個字元以內。
3.  **格式純淨**：請直接提供標題，不要包含任何多餘的解釋或文字。
4.  **語言跟隨**：標題語言必須與使用者最開始傳送的語言相同。
'''

async def gener_title(history: list, length: int = 15):
    client = Chat(system_prompt=gener_title_prompt)

    # process prompt
    prompt_ls = ['以下為兩個人之間的對話，請生成標題: ']
    for h in history:
        if h.get('role') == 'user':
            prompt_ls.append(f'使用者: {h.get("content")}')
        elif h.get('role') == 'assistant':
            prompt_ls.append(f'AI: {h.get("content")}')

    think, result, *_ = await client.chat(
        '\n'.join(prompt_ls),
        is_enable_tools=False
    )

    return_item = (result[:length]).strip()
    if not return_item:
        for item in reversed(history):
            if item.get('role') == 'user':
                return_item = item.get('content', 'no_title').strip()
                break

    return return_item