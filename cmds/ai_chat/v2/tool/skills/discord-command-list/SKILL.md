---
name: discord-command-list
description: Explore YinXi's commands. List all cogs/commands, search by keyword, or get details of a specific command (name, description, parameters)
---

# Get all Discord commands (YinXi)

## 說明

此工具用來查詢音汐（你）的 Discord 指令資訊。你可以透過四個操作來取得不同層級的資訊。
注意，由該 SKILL 提供的任何指令(commands)列表，並非你可直接使用的工具，這些是使用者可以使用該 Discord bot 的工具。
你可以利用這個工具所提供的資訊，去教導使用者如何使用某個指令。

### Actions

1. **list_cogs** — 列出所有指令分類（Cog）
   - 回傳格式：每行一個 Cog 名稱
   - 適用場景：想概覽音汐有哪些功能分類時

2. **list_commands** — 列出所有分類及其旗下的指令
   - 回傳格式：`{CogName}: {cmd1}, {cmd2}, ...`，每行一個分類
   - 適用場景：想要完整了解音汐能執行哪些指令時

3. **search** — 以關鍵字同時搜尋分類名稱與指令名稱
   - 參數：`keyword`（必要）
   - 回傳格式：
     - `[COG] {name}` — 該分類名稱包含關鍵字
     - `[CMD] {CogName}.{cmdName}` — 該指令名稱包含關鍵字
   - 適用場景：使用者問「有沒有XX功能」、「怎麼XX」時，先用此查找相關指令

4. **get_command_info** — 取得指定指令的詳細資訊
   - 參數：`command_name`（必要）
   - 回傳格式：
     ```
     Name: {指令中文名稱}
     Description: {指令中文描述}
     Parameters:
       - {param_name} (required: true/false): {參數說明}
     ```
   - 適用場景：需要告訴使用者某指令怎麼用、需要哪些參數時