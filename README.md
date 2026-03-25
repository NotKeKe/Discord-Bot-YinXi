# 🎶 音汐 (Yin-Xi) Discord 機器人 🤖
<p align="center">
  <img src="https://github.com/NotKeKe/Discord-Bot-YinXi/blob/main/assests/botself.png?raw=true" width = "300" height = "300"/>
</p>

<p align="center">
    <small>(cogview-3-flash 幫他畫了 6 根手指ww)</small>
</p>

**🔗 Bot 邀請連結:**
- [URL](https://discord.com/oauth2/authorize?client_id=990798785489825813)

這是一個 Discord 機器人專案，包含多種功能，例如音樂播放、AI 聊天、小遊戲、以及與 Hypixel SkyBlock 相關的功能。 <br><br>
可以使用以下 Deepwiki.md 連結來瀏覽此專案介紹，或者詳閱接下來的說明 來使用此專案。
- [Deepwiki.md](https://github.com/NotKeKe/Discord-Bot-YinXi/blob/main/assests/Discord-Bot-YinXi_wiki_20250613.md)

## 閱前提醒
*   不建議自己 clone 此專案下來用，因為他大概率是啟動不了的，或許拿來學習比較好w<br>
    畢竟他功能挺雜，有 aiohttp, chromadb, openai, MongoDB 之類的

## ✨ 特色
*   **音樂播放**: 支援播放 YouTube 影片音樂。
*   **AI 聊天**: 透過 AI 進行對話。
*   **小遊戲**: 例如無限圈圈叉叉遊戲。
*   **SkyBlock 相關**: 提供 SkyBlock 遊戲資訊和追蹤功能。
*   **翻譯**: 支援 AI 多語言翻譯。
*   **提醒**: 時間到的時候通知你設定的提醒事項。
*   **通知**: YouTube 通知功能。
*   **多語言支持**: 目前支援使用 `zh-TW`, `zh-CN`, `en-US`。

## 🚀 使用方法
- `/help` 快速取得該 Bot 的概略功能。

### 💡 常用指令範例
以下是一些常用的指令範例，讓您快速上手：
*   `/play [歌曲名稱/URL]`：播放 YouTube 上的音樂。
*   `/chat [您的訊息]`：與 AI 進行對話。
    > (20250806 將整體架構修改，正是支援異步)
*   `/remind [時間] [提醒事項]`：讓 Bot 提醒你要做什麼事情。
    > (20250809 轉為使用 MongoDB 存儲)
*   `/翻譯 [語言] [文字]`：用 AI 將文字翻譯成指定語言。
*   `/minecraft_server_status`：獲得某個 Minecraft 伺服器的狀態。
*   `/news`：獲取最新新聞。
*   `/nasa`：獲取 NASA 每日圖片。
*   `/gif [關鍵字]`：搜尋並發送 GIF。
*   `/歌詞搜尋 [歌曲名稱]`：搜尋歌曲歌詞。

## 成就
*   **[2025/07/08]** 完成 **i18n**，prefix + slash command i18n
    *   可在 [core/locales](core/locales) 查看與 Gemini 2.5 pro 的 `對話紀錄` 與 `提示詞`
*   **[2025/08/06]** 將此專案接入本地 MongoDB，並將 `chat` 相關命令重寫，以支援異步 function 調用
    > 如果之後有機會能將整個 Project 改為使用 MongoDB的話，應該就可以直接用 `git clone` 的方式拿下來用

## ⚡ Quick Start
- 儘管該專案配置了 Docker 相關設定，仍然**不建議自行部署**。
- 因為專案當初使用了大量的 JSON 作為儲存，並且檔案不存在時不會有相關的錯誤處理。
- 並且專案設計之初，並未使用任何較為嚴格的的 type checking，所以可能有一些淺在問題。
<details>
<summary>
Quick Start & env & Json
</summary>

**❗建議使用 Python 3.13+ 以上的環境❗**

**請先設定 `.env` 檔案**:
* 請參考以下「配置設定 - 環境變數」部分，建立並填寫您的 `.env` 檔案。 <br>
**！務必在 .env 內填上 `DISCORD_TOKEN`！**<br><br>

**選項一** 使用 **[Docker](https://www.docker.com/)** (使用 docker 才會包括 fastapi 與 MongoDB 的部分):
```bash
# 將專案克隆至本地目錄
git clone https://github.com/NotKeKe/Discord-Bot-YinXi.git

# 進入專案目錄
cd Discord-Bot-YinXi

# 使用 docker compose 執行
docker-compose up -d
```

**選項二** 使用 **[uv](https://github.com/astral-sh/uv)**:
1. **與專案環境同步**:
    ```bash
    uv sync
    ```
2. **啟動機器人**:
    ```bash
    uv run newbot2.py
    ```

**選項三** 使用 **[pm2](https://pm2.keymetrics.io/)**:
1. **確保你的設備環境內有 `node.js` 與 `npm`**
2. **安裝 pm2**:
    ```bash
    npm install -g pm2
    ```
3. **安裝依賴與啟動Bot**:
    ```bash
    pip install -r requirements.txt
    ./start_run_in_docker_pm2.sh
    ```

    - 如果**無法使用**的話 建議先使用以下指令 
        ```bash
        cd ENTER_YINXI_BOT_PATH
        chmod +x start_run_in_docker_pm2.sh
        ```

**選項四** 使用 **[newbot2.bat](newbot2.bat)** (僅 windows)
1. **安裝依賴**:
    ```bash
    pip install -r requirements.txt
    ```
2. **啟動機器人**:
    ```bash
    newbot2.bat
    ```

## ⚙️ 配置設定

### 🔑 環境變數 (`.env`)

為了讓專案正常運行，您需要建立一個 `.env` 檔案，並在其中設定必要的環境變數。

`.env` 檔案的範例如下：

```
# 其他可能需要的環境變數，例如：
DISCORD_TOKEN = YOUR-DISCORD-BOT-TOKEN
# APPLICATION_ID = ...
HYPIXEL_API_KEY = ... # 因為一些原因 他現在暫時用不了
tmp_hypixel_api_key = YOUR-HYPIXEL-API-KEY

# 以下為 llm api，可以根據需要選擇使用
zhipuAI_KEY = ...
huggingFace_KEY = ...
openrouter_KEY = ...
gemini_KEY = ...
mistral_KEY = ...
cerebras_KEY = ...

news_api_KEY = ... # `/新聞` 的 apiKEY
nasa_api_KEY = ... # `/nasa每日圖片` 的 apiKEY
unsplash_api_access_KEY = ... # `/看圖` 的 apiKEY
embed_default_link = ... # 會顯示在 embed 的 author url
KeJC_ID = ... # 基本上這是為了一些只有 owner 才會用的指令所設計的，例如 `/reload`
# YouTube_PoToken = ...
# YouTube_visitorData = ...
yinxi_base_url = https://yinxi.keketw.dpdns.org
GIPHY_KEY = ... # `/gif` 的 apiKEY
GENIUS_ACCESS_TOKEN = ... # `/歌詞搜尋` 的 apiKEY
```

請根據您的實際需求填寫這些變數。

### 📁 重要的 JSON 檔案

以下是一些在 `.gitignore` 中被忽略的 JSON 檔案，它們可能包含專案運行所需的配置或數據。這些檔案通常需要您手動建立或由專案運行時自動生成。如果專案無法正常啟動，請檢查這些檔案是否存在並包含正確的內容。

*   `setting.json`: 這個檔案可能包含專案的通用設定或配置。
*   `cmds/skyblock_commands_foldor/test.json`: 這個檔案可能用於 SkyBlock 相關功能的測試數據或配置。
*   `cmds/data.json/` 目錄下的檔案：
    *   `簽到.json`
    *   `admins.json`
    *   `chat_channel_modelSelect.json`
    *   `chat_history_forchannel.json`
    *   `chat_history.json`
    *   `chat_human_summary.json`
    *   `chat_human.json`
    *   `chat_personality.json`
    *   `chat_style_train.json`
    *   `counting.json`
    *   `country.json`
    *   `events_record.json`
    *   `giveaway.json`
    *   `guild_join.json`
    *   `keep.json`
    *   `levels.json`
    *   `music_personal_list.json`
    *   `music.json`
    *   `on_presence_update.json`
    *   `skyblock_auction_item_tracker.json`
    *   `skyblock_bazaar_item_tracker.json`
    *   `skyblock_events_channels.json`
    *   `weather_messages.json`
    *   `world_channels.json`
    *   `youtube_update_channels.json`

</details>

## 🤝 貢獻指南
我們歡迎任何形式的貢獻！如果您想為**音汐機器人**做出貢獻，請遵循以下步驟：
1. 給我 Star 來支持我!

## ❓ 常見問題 (FAQ)
*   我遇到了一個錯誤，我要怎麼回報?
    - 使用 `/錯誤回報` 指令，來進行錯誤回報。
    - 參考 [聯絡與支援](#contact-support)
    - 就算您只是發現一個很小的錯誤，也歡迎告知我!

<p id="contact-support">

## 📞 聯絡與支援
如果您有任何問題、建議或需要支援，可以透過以下方式聯絡我們：
*   **Discord 伺服器**: [Discord Server](https://discord.gg/MhtxWJu)
*   至 GitHub 的 [Issues](https://github.com/NotKeKe/Discord-Bot-YinXi/issues/new) 註明您的問題或建議。
*   在 Discord 伺服器中對 音汐 使用 `/錯誤回報` 來回報任何問題。

## 📄 授權
- [LICENSE-MIT](LICENSE)

## TODO & DONE
[TODO](https://github.com/NotKeKe/Discord-Bot-YinXi/blob/main/assests/TODO.md)  
[DONE](https://github.com/NotKeKe/Discord-Bot-YinXi/blob/main/assests/DONE.md)