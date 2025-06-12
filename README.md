# 音汐 (Yin-Xi) Discord 機器人
<p align="center">
  <img src="https://github.com/NotKeKe/Discord-Bot-YinXi/tree/main/assets/botself.png?raw=true" width = "100" height = "100"/>
</p>

**🔗 Bot 邀請連結:**
- [URL](https://discord.com/oauth2/authorize?client_id=990798785489825813)

這是一個 Discord 機器人專案，包含多種功能，例如音樂播放、AI 聊天、小遊戲、以及與 Hypixel SkyBlock 相關的功能。

## 特色
*   **音樂播放**: 支援播放 YouTube 影片音樂。
*   **AI 聊天**: 透過 AI 進行對話。
*   **小遊戲**: 例如無限圈圈叉叉遊戲。
*   **SkyBlock 相關**: 提供 SkyBlock 遊戲資訊和追蹤功能。
*   **翻譯**: 支援 AI 多語言翻譯。
*   **通知**: YouTube 通知功能。

## 使用方法
- `/help` 快速取得該 Bot 的概略功能。

## Quick Start

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

## 配置設定

### 環境變數 (`.env`)

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

### 重要的 JSON 檔案

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