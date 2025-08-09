with open('test.md', 'r', encoding='utf-8') as f:
    content = f.read()

def split_str_by_len_and_backtick(text: str, chunk_size: int = 1800) -> list[str]:
    def go_next_chuck(curr_str_len: int, new_line: str) -> bool:
        return curr_str_len + (1 if curr_str_len > 0 else 0) + len(new_line) > chunk_size
    
    lines = text.splitlines()
    in_backtick = False
    
    str_len = 0
    chunks: list[list[str]] = []
    chunk: list[str] = []
    
    curr_lang = ''
    
    for line in lines:    
        if line.strip().startswith('```'):
            in_backtick = not in_backtick
            
            if in_backtick:
                curr_lang = line[3:].strip()
            else:
                curr_lang = ''
                
        if go_next_chuck(str_len, line): # 如果要分割了，就加進下一個 chunk
            if in_backtick: 
                chunk.append('```')
                chunks.append(chunk) # 將現有 chunk 存入 chunks

                # new chunk
                append_str = f'```{curr_lang}\n' if curr_lang else '```\n'
                chunk = [append_str, line]
                str_len = len(append_str) + 1 + len(line)
            else:
                chunks.append(chunk)
                chunk = [line]
                str_len = len(line)

        else: # 加進原chunk
            chunk.append(line)
            str_len += (1 if str_len > 0 else 0) + len(line)

    if chunk:
        # 我不清楚為什麼他會少加一個chunk，但GPT5告訴我這樣做後就正常了
        chunks.append(chunk)

    return ['\n'.join(chunk) for chunk in chunks]


result = split_str_by_len_and_backtick(content)

print(result[0][-100:])
print(result[1][:100])
# print(len(result))
# print()
# with open('test2.md', 'w', encoding='utf-8') as f:
#     f.write('\n'.join(result))