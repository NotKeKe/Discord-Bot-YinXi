from .chat import Chat

gener_title_prompt = '''
# Role
You are a concise conversation titler.

# Rules
1. Output ONLY the title. No quotes, no explanations, no "Title:".
2. LANGUAGE MATCH: The title must be in the same language as the user's message.
3. Length: Keep it between 2 to 6 words.
4. Goal: Extract the core topic of the input.

# Few-Shot Examples
User: 如何在 WSL2 上限制記憶體使用量？
Assistant: WSL2 記憶體限制設定
User: How to fix a Docker container restart loop?
Assistant: Fixing Docker Restart Loop
User: 推薦幾款好玩的電腦節奏遊戲
Assistant: 電腦節奏遊戲推薦

# Task
User: {{user_message}}
Assistant:
'''

async def gener_title(history: list, length: int = 15):
    try:
        client = Chat(model='ai-local:qwen3-1.7b', system_prompt=gener_title_prompt)

        # process prompt
        prompt_ls = ['The following is a conversation between a user and an AI. Please generate a title for the conversation.']
        for h in history:
            if h.get('role') == 'user':
                prompt_ls.append(f'User: \n<>\n{h.get("content")}\n</>')
            elif h.get('role') == 'assistant':
                prompt_ls.append(f'AI: \n<>\n{h.get("content")}\n</>')

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