from cmds.AIsTwo.base_chat import true_zhipu, ollama, gemini
from cmds.AIsTwo.tool_map import func_map
from cmds.AIsTwo.tool_map import tools_descrip, current_time
from cmds.AIsTwo.utils import to_user_message, to_system_message
import orjson
import traceback
from typing import Union

system_prompt = '''
You should decide according to the context if you need to use the following tools.
[current_time, calculate, search, image_generate, video_generate, UnixToReadable, image_read, knowledge_search, knowledge_save]
current_time: to get current time.
calculate : to calculate the result of a mathematical expression.
search : to search some information from the internet.
image_generate, video_generate: generate images or videos based on given inputs (text).
UnixToReadable : convert Unix timestamp into readable format(e.g 1640932875 -> 2022-01-01T01:01:35+00:00).
image_read: to let you know what is the image describing.
knowledge_search, knowledge_save: to search and save information in a knowledge database. (every arguments must in Chinese)

if there is no need to use the tools, just return "false".

'''

some_gemini_models_function_calling = [
    'gemini-2.0-flash',
    'gemini-2.0-flash-lite',
    'gemini-1.5-flash',
    'models/gemini-1.5-pro'
]

def get_tool_results(tool_calls: list) -> str:
    try:
        result = []
        is_curretTime = False
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            # print(f'{tool_call=}\n{tool_call.function.arguments=}')
            arguments = tool_call.function.arguments
            args = orjson.loads(arguments) if type(arguments) != dict else arguments
            print(f'{tool_name}: {args}')
            try: result.append(f'{tool_name}: {func_map[tool_name](**args)}')
            except: traceback.print_exc()

            if tool_name == 'current_time': is_curretTime = True
        
        if not is_curretTime:
            result.append(f'現在時間為: {current_time()}')

        func_results:str = '\n\n\n'.join(result)
        # print(func_results)
        return func_results
    except: traceback.print_exc()

def delete_func(tmp_tools_descrip: list, delete_func_name: Union[str, list]):
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

def ifTools_zhipu(messages: list, delete_func_name: Union[str, list] = None):
    try:
        tmp_tools_descrip = list(tools_descrip)
        if delete_func_name:
            tmp_tools_descrip = delete_func(tmp_tools_descrip, delete_func_name)
        response = true_zhipu.chat.completions.create(
            model="glm-4-flash",  # 请填写您要调用的模型名称
            messages=to_system_message(system_prompt) + messages,
            tool_choice='auto',
            tools=tmp_tools_descrip,
            temperature=0.8
        )

        if response.choices[0] is None: raise '沒有回應'

        # 不需要tools則跳出while迴圈並return
        if response.choices[0].message.tool_calls is None: return messages

        # tools結果
        func_results = get_tool_results(response.choices[0].message.tool_calls)
        
        messages += to_user_message(f'tool輸出為: {func_results}')
        return messages
    except: return messages

def ifTools_ollama(messages: list, delete_func_name: Union[str, list] = None):
    tmp_tools_descrip = list(tools_descrip)
    if delete_func_name:
        tmp_tools_descrip = delete_func(tmp_tools_descrip, delete_func_name)
    response = ollama.chat.completions.create(
        model='qwen3:4b-q8_0',
        messages=to_system_message(system_prompt) + messages[-2:],
        stream=False,
        tool_choice="auto",
        tools=tools_descrip
    )

    if response.choices[0] is None: raise '沒有回應'

    # 不需要tools則跳出while迴圈並return
    if response.choices[0].message.tool_calls is None: return messages

    # tools結果
    func_results = get_tool_results(response.choices[0].message.tool_calls)
    
    messages += to_user_message(f'tool輸出為: {func_results}')
    return messages
    
def ifTools_gemini(messages: list, delete_func_name: Union[str, list] = None):
    try:
        tmp_tools_descrip = list(tools_descrip)
        if delete_func_name:
            tmp_tools_descrip = delete_func(tmp_tools_descrip, delete_func_name)
        response = gemini.chat.completions.create(
            model='gemini-2.0-flash',
            messages=to_system_message(system_prompt) + messages,
            stream=False,
            tool_choice="auto",
            tools=tools_descrip
        )

        if response.choices[0] is None: raise '沒有回應'

        # 不需要tools則跳出while迴圈並return
        if response.choices[0].message.tool_calls is None: return messages

        # tools結果
        func_results = get_tool_results(response.choices[0].message.tool_calls)
        
        messages += to_user_message(f'tool輸出為: {func_results}')
        return messages
    except: 
        traceback.print_exc()
        return messages