# 🎶 音汐 (Yin-Xi) Discord 機器人 🤖
<p align="center">
  <img src="https://github.com/NotKeKe/Discord-Bot-YinXi/blob/main/assests/botself.png?raw=true" width = "300" height = "300"/>
</p>

( cogview-3-flash 幫他畫了 6 根手指ww )

**🔗 Bot 邀請連結:**
- [URL](https://discord.com/oauth2/authorize?client_id=990798785489825813)

這是一個 Discord 機器人專案，包含多種功能，例如音樂播放、AI 聊天、小遊戲、以及與 Hypixel SkyBlock 相關的功能。 <br><br>
可以使用以下 Deepwiki.md 連結來瀏覽此專案介紹，或者詳閱接下來的說明 來使用此專案。
- [Deepwiki.md](https://github.com/NotKeKe/Discord-Bot-YinXi/blob/main/assests/Discord-Bot-YinXi_wiki_20250613.md)

## ✨ 特色
*   **音樂播放**: 支援播放 YouTube 影片音樂。
*   **AI 聊天**: 透過 AI 進行對話。
*   **小遊戲**: 例如無限圈圈叉叉遊戲。
*   **SkyBlock 相關**: 提供 SkyBlock 遊戲資訊和追蹤功能。
*   **翻譯**: 支援 AI 多語言翻譯。
*   **通知**: YouTube 通知功能。

## 🚀 使用方法
- `/help` 快速取得該 Bot 的概略功能。

### 💡 常用指令範例
以下是一些常用的指令範例，讓您快速上手：
*   `/play [歌曲名稱/URL]`：播放 YouTube 上的音樂。
*   `/chat [您的訊息]`：與 AI 進行對話。
*   `/翻譯 [語言] [文字]`：將文字翻譯成指定語言。
*   `/news`：獲取最新新聞。
*   `/nasa`：獲取 NASA 每日圖片。
*   `/gif [關鍵字]`：搜尋並發送 GIF。
*   `/歌詞搜尋 [歌曲名稱]`：搜尋歌曲歌詞。

## ⚡ Quick Start
**！建議使用 Python 3.13+ 以上的環境！**

1.  **安裝依賴**:
    ```bash
    pip install -r requirements.txt
    ```
2.  **設定 `.env` 檔案**:
    請參考以下「配置設定 - 環境變數」部分，建立並填寫您的 `.env` 檔案。 <br>
    **！務必在 .env 內填上 `DISCORD_TOKEN`！**
3.  **啟動機器人**: <br>
    - **選項1: 使用 終端 執行**
        ```bash
        python newbot2.py
        ```
    - **選項2: 使用 pm2 執行**
        ```bash
        npm install pm2 -g
        ./start_run_in_docker_pm2.sh
        ```
        - 如果**無法使用**的話 建議先使用以下指令 
            ```bash
            cd YOUR_PATH_HERE
            chmod +x start_run_in_docker_pm2.sh
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

## 🤝 貢獻指南
我們歡迎任何形式的貢獻！如果您想為音汐機器人做出貢獻，請遵循以下步驟：
1. 想不到吧 這裡也是空的w

## ❓ 常見問題 (FAQ)
*   有沒有英文版或者其他語言的音汐機器人?
    *   目前暫時沒有對指令以及指令描述做翻譯，只有中文版，並且很多檔案主要還是用中文編寫的，或許之後哪一天我會突然想翻譯他w

## 📞 聯絡與支援
如果您有任何問題、建議或需要支援，可以透過以下方式聯絡我們：
*   **Discord 伺服器**: [Discord Server](https://discord.gg/MhtxWJu)
*   至 GitHub 的 Issues 註明您的問題或建議。
*   在 Discord 伺服器中對 音汐 使用 `/錯誤回報` 來回報任何問題。

## 📄 授權
- 暫無授權資訊。
