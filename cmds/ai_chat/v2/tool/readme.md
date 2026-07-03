## skill 的方式

### 說明
在提示詞裡面，先去列出全部的工具 (類似 skill 的方式)
ai 調用 use skill 工具，回傳 skill 所包含的 SKILL.md 之類的
與一般 skill 不同的地方是，這個架構要將這個 skill 轉換成傳統工具，給 AI 使用
接著這個加進來的工具，就會一直在 AI 的上下文當中

### 目的
透過這種類似 skill 的方式，假設一個工具需要**很長的提示詞**
如此便可讓提示詞在被使用時才加進 context 內

### SKILL.md 格式說明
一般情況下，skill.md 一定會有
```markdown
---
name: current-time
description: asdasd
---
```
但可能沒有內文

### tool.json
由於要將工具轉為 openai 可用工具，所以額外多了 tool.json，用來儲存 params 的說明 (name 跟 description 已經有在 SKILL.md 內了)
格式如下: 
```json
{
    "type": "object",
    "properties": {
        "time_offset": {
            "type": "integer",
            "description": "Timezone offset in hours; defaults to 8 if not provided"
        }
    },
    "required": []
}
```