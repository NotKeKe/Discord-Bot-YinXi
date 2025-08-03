## TODO

~~可用表情符號: ✅、⬜~~<br>
## 按照任務優先程度排序
[] ai_three 的輸出中暫停功能 (使用 task 以及 task.cancel() )
[] ai_three 歷史紀錄存儲

| Tasks | 類型 | 狀態 | 備註 |
|------|------|------|------|
| 1. 製作一個 yt-dlp fastapi，用來抓取每日最受歡迎的音樂，並下載到本地<br>2. 將音樂功能分開到不同的 bot 上<br> | 功能開發 | ⬜ 未完成 | 1. 讓 bot 能夠選擇 穩定的api來源 或者 前面提到的yt-dlp api <br>2. yt-dlp需要創建為每日任務<br>3. bot需使用 logging 做日誌輸出<br>4. yt-dlp可使用 key-value 的方式來儲存影片，例如`{ "name": {"filename": "test.mp4", "video_url": "https://www.youtube.com", "thumbnail": ... ...} }` |
| 刪除影片下載功能，或是修好他 | Bug 修復 | ⬜ 未完成 |
| 將各種功能分支到不同的bot上 | 功能開發 | ⬜ 未完成 |
| 在有關伺服器的功能上，加上網頁操作的功能 | 功能開發 | ⬜ 未完成 | 總有一天會完成的哈哈 |