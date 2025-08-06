import discord
from discord.ext import commands
from typing import Tuple, Union
from typing import AsyncGenerator
from openai.types.chat import ChatCompletionChunk, ChatCompletion, ChatCompletionMessage
import orjson

from ..utils import model_select, to_system_message, to_user_message, get_think, clean_text, split_provider_model
from ..utils.config import base_system_prompt, summarize_history_system_prompt

# tool
from ..tools import tool_description, tool_map

from core.functions import is_async, image_to_base64, current_time
from core.classes import get_bot

class Chat:
    def __init__(self, model: str = None, system_prompt: str = '', ctx: commands.Context = None):
        if not model: model = 'qwen-3-32b'
        self.model = model
        self.ctx = ctx
        self.userID: int = ctx.author.id if ctx else None

        self.client = None

        self.system_prompt = str(base_system_prompt) if system_prompt in ('', None) else system_prompt

    async def re_model(self, model: str):
        """重新選擇模型

        Args:
            model (str): 傳入模型名稱
        """        
        self.model = model
        self.client = await model_select(model)

    def re_system_prompt(self, system_prompt: str) -> bool:
        """重新設定系統提示詞


        Args:
            system_prompt (str): 系統提示詞

        Returns:
            bool: True or (False if failed)
        """        
        if not isinstance(system_prompt, str): return False

        self.system_prompt = system_prompt
        return True
    
    def get_extra_user_info(self) -> str:
        if not self.userID: return ''

        bot = get_bot()
        name = (bot.get_user(self.userID)).global_name
        preference = None
        info = None

        return (
'''
## 關於 {name} 的資訊
- 偏好: {preference}
- 其他資訊: {info}
'''.format(name=name, preference=preference, info=info)
)
        #TODO

    def process_tool_decrip(self, delete_func_name: Union[str, list, None] = None):
        tmp_tools_descrip = list(tool_description)

        for tool in tmp_tools_descrip:
            tool_name = tool['function']['name']
            if type(delete_func_name) == list:
                if tool_name in delete_func_name:
                    delete_func_name.remove(tool_name)
                    tmp_tools_descrip.remove(tool)
                    
                    if not delete_func_name:
                        break
            elif type(delete_func_name) == str:
                if tool_name == delete_func_name: 
                    tmp_tools_descrip.remove(tool)
                    break

        return tmp_tools_descrip

    async def process_stream(self, stream: AsyncGenerator[ChatCompletionChunk, None]) -> Tuple[str, str, list]:
        think = []
        result = []
        tool_calls = []
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.tool_calls:
                # 如果有工具調用，累積工具調用資訊
                if not tool_calls:
                    tool_calls.extend([{} for _ in delta.tool_calls])
                
                for i, tool_call_chunk in enumerate(delta.tool_calls):
                    if tool_call_chunk.function.name:
                        tool_calls[i]['name'] = tool_call_chunk.function.name
                    if tool_call_chunk.function.arguments:
                        tool_calls[i].setdefault('arguments', '')
                        tool_calls[i]['arguments'] += tool_call_chunk.function.arguments
                    if tool_call_chunk.id:
                        tool_calls[i]['id'] = tool_call_chunk.id

            if delta.content:
                result.append(delta.content)
            if hasattr(delta, "reasoning"):
                if delta.reasoning:
                    think.append(delta.reasoning)

        result = ''.join(result)
        think = ''.join(think)

        think = get_think(''.join(result)) if not think else think
        result = clean_text(result)
        
        return think, result, tool_calls
    
    async def process_completion(self, response: ChatCompletion) -> Tuple[str, str, list, int]:
        think: str = ""
        result: str = ""
        tool_calls: list = []

        message: ChatCompletionMessage = response.choices[0].message

        if message.tool_calls:
            for tool_call in message.tool_calls:
                tool_calls.append({
                    'id': tool_call.id,
                    'name': tool_call.function.name,
                    'arguments': tool_call.function.arguments
                })

        if message.content:
            result = message.content

        if (hasattr(message, 'reasoning_content')) is True:
            think = message.reasoning_content
        else:
            think = get_think(result)

        result = clean_text(result)

        total_tokens = response.usage.total_tokens
        
        return think, result, tool_calls, total_tokens

    
    async def process_tool_calls(self, tool_calls: list, history: list):
        '''Love gemini :>
        call function and add result to history
        '''
        if not (tool_calls and all('id' in tc and 'name' in tc and 'arguments' in tc for tc in tool_calls)):
            return

        assistant_message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": tc['id'],
                    "type": "function",
                    "function": {"name": tc['name'], "arguments": tc['arguments']}
                } for tc in tool_calls
            ]
        }
        history.append(assistant_message)

        for tool_call in tool_calls:
            tool_call_id = tool_call['id']
            function_name = tool_call['name']
            function_response = "Error: An unknown error occurred."

            try:
                function_to_call = tool_map.get(function_name)
                if not function_to_call:
                    history.append(
                        {
                            "tool_call_id": tool_call_id,
                            "role": "tool",
                            "name": function_name,
                            "content": f"Function '{function_name}' not found in tool map."
                        }
                    )
                    return 

                function_args = orjson.loads(tool_call['arguments'])
                if not isinstance(function_args, dict):
                    raise TypeError("Function arguments must be a dictionary.")

                if is_async(function_to_call):
                    function_response = await function_to_call(**function_args)
                else:
                    function_response = function_to_call(**function_args)

            except orjson.JSONDecodeError:
                function_response = f"Error: Failed to parse arguments for '{function_name}'. Arguments must be valid JSON."
            except (TypeError, ValueError) as e:
                function_response = f"Error: Failed to call '{function_name}'. Details: {e}"
            except Exception as e:
                function_response = f"Error: An unexpected error occurred while calling '{function_name}'. Details: {e}"
            
            # 4. 將結果添加到歷史記錄
            history.append(
                {
                    "tool_call_id": tool_call_id,
                    "role": "tool",
                    "name": function_name,
                    "content": str(function_response), # Ensure response is a string
                }
            )

    async def process_user_prompt(self, user_prompt: str, image: discord.Attachment = None, text_file: discord.Attachment = None, url: str = None) -> list:
        image_content = None
        text_file_content = None
        if text_file:
            text_file_content = await text_file.read()
        if image:
            image_content = await image_to_base64(image.url)
        
        prompt = (
            user_prompt,
            f'The following is the `image` provided by the user: ```{image_content}```' if image_content else '',
            f'The following is the `url` provided by the user: `{url}`' if url else ''
            f'The following is the `file` provided by the user: ```{text_file_content}```' if text_file_content else ''
        )

        return to_user_message(('\n\n'.join(prompt)).strip())

    async def chat(
                self,
                prompt: str,
                is_vision_model: bool = False,
                model: str = None,
                temperature: float = 1.0,
                history: list = None,
                max_tokens: int = None,
                is_enable_tools: bool = True,
                top_p: float = 1.0,
                delete_tools: Union[str, list] = None,
                timeout: float = None,
                url: list = None,
                image: discord.Attachment = None,
                text_file: discord.Attachment = None,
                custom_system_prompt: str = None
            ) -> Tuple[str, str, list]:
        if model:
            await self.re_model(model)
        else:
            self.client = await model_select(self.model)

        if not history: history = []

        provider, self.model = split_provider_model(self.model)
        if not self.model: return '', f'{model} is not available.', history

        extra_user_info = self.get_extra_user_info()
        system_prompt = self.system_prompt + extra_user_info

        system = to_system_message(custom_system_prompt if custom_system_prompt else system_prompt)

        history += await self.process_user_prompt(prompt, image, text_file, url)

        async def call():
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=system + history,
                max_completion_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stream=False,
                timeout=timeout,
                tools=self.process_tool_decrip(delete_tools) if is_enable_tools else None,
                tool_choice='auto' if is_enable_tools else 'none'
            )
            return resp
        
        completion = await call()

        call_times = 0

        while call_times < 3: # 3 times to call functions
            think, result, tool_calls, total_tokens = await self.process_completion(completion)
            if tool_calls:
                await self.process_tool_calls(tool_calls, history)
                completion = await call()
                call_times += 1
            else:
                break

        history.append({
            "role": "assistant",
            "content": result.strip(),
            **({'reasoning': think.strip()} if think else {})
        })

        if provider.lower() in ('ollama', 'lmstudio') and total_tokens >= 30000: await self.summarize_history(history)
        elif total_tokens > 62000: await self.summarize_history(history)

        return think, result, history
            
    async def summarize_history(self, history: list):
        ls_prompt = []
        for h in history:
            role = h.get('role', '')
            content = h.get('content', '')

            if role == 'user':
                ls_prompt.append(f'User: 「{content})」')
            elif role == 'assistant' and content:
                ls_prompt.append(f'Assistant: 「{content}」')

        think, result, history = await self.chat(
            prompt='\n'.join(ls_prompt),
            is_enable_tools=False,
            custom_system_prompt=summarize_history_system_prompt,
            top_p=0.5
        )

        history = to_user_message(f'# 以下是針對先前的對話總結 (總結時間: {current_time()}):\n```{result}```')