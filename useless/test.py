original_text = '''
不好意思，我剛才用了 Markdown 表格，違反了「禁止使用表格」的規則。下面把先前的比較內容改成純文字的項目符號版，讓你可以直接閱讀。\n\n---\n\n## 為什麼會想換成 MongoDB？\n\n- **多使用者同時存取**  \n  - JSON 同時被多個指令讀寫時會出現檔案鎖定或競爭條件。MongoDB 原生支援並發連線，寫入、讀取都是 atomic 的。  \n\n- **資料量漸增**  \n  - 若開始記錄使用者統計、排行榜或每日活動紀錄，JSON 檔案會變得又大又慢。MongoDB 會自行建立索引、分片，查詢速度不會因資料量變大而退化。  \n\n- **靈活的查詢**  \n  - 例如「找出過去 7 天內發言次數最高的 10 位使用者」可以直接在資料庫用 filter、aggregation 完成，不必一次把整個檔案載入記憶體。  \n\n- **備份與恢復**  \n  - MongoDB 可以設定自動快照、備份腳本，甚至使用雲端 Atlas 的一鍵還原。JSON 若只靠手動備份或 git，有遺失風險。  \n\n- **可擴充的結構**  \n  - 想在未來加新欄位（等級、勳章、偏好設定）時，BSON 允許文件自行增減欄位；JSON 則需要搬遷程式或重新寫入。  \n\n---\n\n## 為什麼還可以繼續使用 JSON？\n\n- **簡單、零成本**  \n  - 只要有一個檔案就能跑，部署到 Heroku、Replit、Docker 都不需要額外資料庫服務。  \n\n- **開發門檻低**  \n  - 讀寫只需要 `json.load` / `json.dump`，不必學 async driver、連線池、錯誤處理。  \n\n- **資料量真的很小**  \n  - 若 Bot 只存設定檔、冷卻時間、少量使用者偏好，幾 KB–MB 的檔案毫無壓力。  \n\n- **部署環境限制**  \n  - 有些免費的 Discord Bot 托管平台只允許本機磁碟，這時 JSON 是唯一選擇。  \n\n---\n\n## 把 JSON 換成 MongoDB 的實作要點（使用 Motor – async）\n\n1. **建立連線（放在 bot 初始化時）**  \n   ```python\n   from motor.motor_asyncio import AsyncIOMotorClient\n\n   client = AsyncIOMotorClient(\"mongodb://localhost:27017\")   # 或 Atlas 連線字串\n   db = client[\"discord_bot\"]\n   col_user = db[\"user_data\"]          # 存每位使用者的設定\n   ```\n\n2. **讀取資料**  \n   ```python\n   async def get_user_data(user_id: int) -> dict:\n       doc = await col_user.find_one({\"_id\": str(user_id)})\n       if doc is None:                     # 若無資料就給預設值\n           return {\"_id\": str(user_id), \"xp\": 0, \"level\": 1}\n       return doc\n   ```\n\n3. **更新資料（upsert）**  \n   ```python\n   async def set_user_data(user_id: int, data: dict):\n       await col_user.update_one(\n           {\"_id\": str(user_id)},\n           {\"$set\": data},\n           upsert=True\n       )\n   ```\n\n4. **範例指令（discord.py）**  \n   ```python\n   @bot.command()\n   async def xp(ctx, amount: int):\n       user = await get_user_data(ctx.author.id)\n       user[\"xp\"] += amount\n       await set_user_data(ctx.author.id, user)\n       await ctx.send(f\"{ctx.author.mention} 獲得了 {amount} XP！\")\n   ```\n\n- **全程 async**：Motor 本身是非同步的，配合 `discord.py` 不會阻塞事件迴圈。  \n- **`_id` 使用字串**：MongoDB 必須唯一，直接把 Discord user ID 轉成字串最簡單。  \n- **`upsert=True`**：一次指令就能「新增或更新」，不必先判斷是否存在。  \n\n---\n\n## 成本與部署注意（純文字列點）\n\n- **伺服器資源**  \n  - JSON：無額外需求。  \n  - 自行部署 MongoDB：需要一台可以跑 `mongod` 的機器（CPU、記憶體）。  \n  - MongoDB Atlas（Free Tier）：雲端託管，免費配額有限（約 512 MiB 儲存、500 MB 傳輸）。\n\n- **連線延遲**  \n  - JSON：本機讀寫，毫秒級。  \n  - 自己部署的 MongoDB：內網或遠端，視網路而定。  \n  - Atlas：跨區域仍在 100‑200 ms 左右，對大多數 Bot 來說足夠。\n\n- **資料備份**  \n  - JSON：手動備份或透過 Git commit。  \n  - MongoDB：可使用 `mongodump`、cron 排程備份。  \n  - Atlas：自動快照與每日備份功能。\n\n- **安全性**  \n  - JSON：靠檔案權限保護。  \n  - MongoDB（自行部署）：需要設定認證、IP 白名單。  \n  - Atlas：內建使用者/密碼、IP 過濾。\n\n- **成本**  \n  - JSON：完全免費。  \n  - 自行部署 MongoDB：需自行負擔伺服器或 VPS 費用。  \n  - Atlas（Free Tier）：免費，但有配額上限；若超出需付費。\n\n---\n\n## 小結與建議（項目符號）\n\n- **先評估規模**  \n  - 每日寫入次數 < 10‑20 次、使用者 < 100，JSON 完全足夠。  \n  - 使用者數超過幾千、需要排行榜或跨伺服器同步時，考慮搬遷到 MongoDB。  \n\n- **抽象資料存取層**  \n  - 把讀寫封裝成 `get_user_data / set_user_data`（async），日後只要改成 MongoDB，其他指令不需要大幅調整。  \n\n- **先測試**  \n  - 在本機安裝 MongoDB（或用 Docker `docker run -d -p 27017:27017 mongo`），跑上面的範例感受延遲與程式碼變動量。  \n\n- **定期備份**  \n  - 無論選 JSON 或 MongoDB，都要記得 **定期備份**（JSON → Git commit，MongoDB → `mongodump`），避免資料遺失。  \n\n---\n\n如果你決定要搬遷，或是想在現有 JSON 上再加上檔案鎖定機制（例如 `filelock`）來避免同時寫入衝突，我可以提供簡易範例。  \n或是想看看在 MongoDB 裡做聚合、排行榜的程式碼，也隨時告訴我喔！祝你的 Bot 越玩越順、資料越安全～ (✿◠‿◠)
'''.strip()

def split_text(text: str, chuck_size: int = 100) -> list[str]:
    def go_next_chuck(curr_str_len: int, text: str) -> bool:
        return curr_str_len + len(text) > chuck_size
    
    lines = text.splitlines()
    in_backtick = False
    
    str_len = 0
    chunks: list[list[str]] = []
    chunk: list[str] = []
    
    curr_lang = ''
    
    for line in lines:
        if line.startswith('```'):
            in_backtick = not in_backtick
            
            if in_backtick:
                curr_lang = line[3:].strip()
            else:
                curr_lang = ''
            
        if go_next_chuck(str_len, line): # 如果要分割了，就加進下一個 chunk
            if in_backtick: 
                chunk.append('```')
                chunks.append(chunk) # 將現有 chunk 存入 chunks

                append_str = f'```{curr_lang}\n' + line

                # new chunk
                chunk = [append_str]
                str_len = len(append_str)
            else:
                chunks.append(chunk)
                chunk = [line]
                str_len = len(line)

        else: # 加進原chunk
            chunk.append(line)
            str_len += len(line)

    if chunk:
        # 我不清楚為什麼他會少加一個chunk，但GPT5告訴我這樣做後就正常了
        chunks.append(chunk)

    return ['\n'.join(chunk) for chunk in chunks]

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
        if line.startswith('```'):
            in_backtick = not in_backtick
            
            if in_backtick:
                curr_lang = line[3:].strip()
            else:
                curr_lang = ''
            
        if go_next_chuck(str_len, line): # 如果要分割了，就加進下一個 chunk
            if in_backtick: 
                chunk.append('```')
                chunks.append(chunk) # 將現有 chunk 存入 chunks

                append_str = f'```{curr_lang}\n' + line

                # new chunk
                chunk = [append_str]
                str_len = len(append_str)
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



result = split_text(original_text)
print(result)
print('\n'.join(result))

# print(split_text(original_text))