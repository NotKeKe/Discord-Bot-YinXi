from .chat import Chat

gener_title_prompt = '''
你是一位專業的「對話摘要標題」生成器。

請根據我提供的對話內容，產出一則精簡、客觀的標題。

請嚴格遵守以下規則：
1. **客觀總結**：標題需準確反映對話主題，不帶個人情感或主觀判斷。
2. **字數限制**：標題不得超過 10 個字元。
3. **格式純粹**：僅輸出標題，不附加說明、標點或其他文字。
4. **語言一致**：標題語言須與使用者最初輸入的語言相同。

進階規則：
5. **主題模糊時**：若對話主題不明確，請選擇最常被提及的概念作為標題核心。
6. **多重主題時**：若對話涵蓋多個主題，請選擇最具代表性、最具資訊密度的主軸。
7. **語言偵測失敗時**：若無法判斷語言，請預設使用繁體中文。
'''

async def gener_title(history: list, length: int = 15):
    try:
        client = Chat(model='glm-4-flash', system_prompt=gener_title_prompt)

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
    except:
        return None