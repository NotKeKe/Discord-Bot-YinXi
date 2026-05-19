# source: 1
import discord
from discord.ext import commands
import yt_dlp
import asyncio

ffmpeg_path = "/bin/ffmpeg"

class MusicCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.song_queue = {}         # {guild_id: [song_data, ...]}
        self.current_song_info = {}  # {guild_id: song_data} 儲存當前歌曲資訊
        self.looping = {}            # {guild_id: bool} 單曲循環狀態 (每個伺服器獨立)
        self.queue_looping = {}      # {guild_id: bool} 列表循環狀態 (每個伺服器獨立)
        self.ytdlp_format = 'bestaudio/best'
        # source: 2
        self.ydl_opts = {
            'format': self.ytdlp_format,  # 選擇最佳音頻格式
            'noplaylist': True,          # 只處理單個視頻 (如果需要播放列表請設為 False 或移除)
            'quiet': True,               # 靜音模式，避免大量輸出
            'simulate': False,           # ***重要：必須設為 False 才能取得可播放 URL***
            # source: 3
            'forceurl': True             # 強制獲取 URL
        }
        self.ffmpeg_options = {
            'options': '-vn'             # '-vn' 表示禁用視頻
        }

    def _get_voice_client(self, ctx):
        """獲取當前伺服器的語音客戶端"""
        return discord.utils.get(self.bot.voice_clients, guild=ctx.guild)

    def _play_next_song(self, ctx):
        """播放隊列中的下一首歌，處理循環邏輯"""
        guild_id = ctx.guild.id
        if guild_id not in self.song_queue:
            # 如果此伺服器沒有隊列了 (可能在播放結束後被清理)
            asyncio.run_coroutine_threadsafe(self._disconnect_if_idle(ctx), self.bot.loop)
            return

        # 檢查單曲循環 (每個伺服器獨立)
        # source: 4
        if self.looping.get(guild_id, False):
            song = self.current_song_info.get(guild_id)
            if song:
                # 使用協程安全地播放 (因為 after 回調不是在 async 環境中)
                asyncio.run_coroutine_threadsafe(self._play_song(ctx, song), self.bot.loop)
            else:
                # 如果不知為何 current_song 不見了，嘗試播放下一首
                self._play_from_queue(ctx, guild_id)
            return

        # 處理隊列
        self._play_from_queue(ctx, guild_id)

    def _play_from_queue(self, ctx, guild_id):
        """從隊列中取出歌曲並播放，處理列表循環"""
        if guild_id in self.song_queue and self.song_queue[guild_id]:
            # 檢查列表循環 (每個伺服器獨立)
            is_queue_looping = self.queue_looping.get(guild_id, False)

            song = self.song_queue[guild_id].pop(0)
            # source: 5
            if is_queue_looping:
                self.song_queue[guild_id].append(song) # 如果列表循環，放回隊列末尾

            # 使用協程安全地播放
            asyncio.run_coroutine_threadsafe(self._play_song(ctx, song), self.bot.loop)
        else:
            # 隊列空了，清理當前歌曲信息，並檢查是否需要斷開
            if guild_id in self.current_song_info:
                del self.current_song_info[guild_id]
            # 使用協程安全地檢查並可能斷開連接
            asyncio.run_coroutine_threadsafe(self._disconnect_if_idle(ctx), self.bot.loop)

    async def _play_song(self, ctx, song):
        """實際播放歌曲，並更新當前歌曲資訊"""
        guild_id = ctx.guild.id
        try:
            # source: 6
            vc = self._get_voice_client(ctx)
            if vc and vc.is_connected():
                # 更新當前播放歌曲資訊
                self.current_song_info[guild_id] = song
                # 播放
                vc.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(song['url'], executable=ffmpeg_path, **self.ffmpeg_options)),
                        after=lambda e: self._handle_after_play(ctx, e)) # 使用新的 after 處理函數
                # source: 7
                vc.source.volume = 0.5 # 預設音量
                await ctx.send(f"▶️ 現在播放: **{song['title']}**")
            # else:
                # 如果 vc 不存在或未連接，理論上不應進入此函數
                # await ctx.send("我沒有連接到語音頻道") # 避免過多訊息
                pass
        except Exception as e:
            print(f"播放歌曲時發生錯誤 (Guild: {guild_id}): {e}")
            await ctx.send(f"❌ 播放歌曲時發生錯誤: {e}")
            # 發生錯誤時，嘗試播放下一首
            self._play_next_song(ctx)

    def _handle_after_play(self, ctx, error):
        """播放結束後的回調函數"""
        if error:
            print(f'播放結束時發生錯誤 (Guild: {ctx.guild.id}): {error}')
            # 可以選擇在這裡發送錯誤訊息給使用者
            # asyncio.run_coroutine_threadsafe(ctx.send(f"播放時遇到錯誤: {error}"), self.bot.loop)

        # 無論是否有錯誤，都嘗試播放下一首
        self._play_next_song(ctx)


    async def _disconnect_if_idle(self, ctx):
        """如果語音頻道內只剩下機器人，則斷開連接"""
        vc = self._get_voice_client(ctx)
        if vc and vc.is_connected() and len(vc.channel.members) == 1: # 頻道中只有機器人
            await self._disconnect_voice(ctx)
            await ctx.send("語音頻道已空，自動離開。")

    async def _disconnect_voice(self, ctx):
        # source: 8
        """斷開語音連線並清理相關狀態"""
        guild_id = ctx.guild.id
        vc = self._get_voice_client(ctx)
        if vc:
            await vc.disconnect()

        # 清理該伺服器的狀態
        if guild_id in self.song_queue:
            del self.song_queue[guild_id]
        if guild_id in self.current_song_info:
            del self.current_song_info[guild_id]
        # source: 9
        if guild_id in self.looping:
            del self.looping[guild_id] # 清理單曲循環狀態
        if guild_id in self.queue_looping:
            del self.queue_looping[guild_id] # 清理列表循環狀態

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')
        # 清理可能殘留的狀態 (如果機器人重啟)
        print("正在清理舊的語音狀態...")
        for guild in self.bot.guilds:
            if guild.id in self.song_queue or guild.id in self.current_song_info or guild.id in self.looping or guild.id in self.queue_looping:
                 vc = discord.utils.get(self.bot.voice_clients, guild=guild)
                 if vc and vc.is_connected():
                    await vc.disconnect()
                 if guild.id in self.song_queue: del self.song_queue[guild.id]
                 if guild.id in self.current_song_info: del self.current_song_info[guild.id]
                 if guild.id in self.looping: del self.looping[guild.id]
                 if guild.id in self.queue_looping: del self.queue_looping[guild.id]
        print("清理完成。")


    @commands.command(name="join", aliases=['j'], help="讓機器人加入您所在的語音頻道")
    async def join(self, ctx):
        """指令：加入語音頻道"""
        if ctx.author.voice is None:
            await ctx.send("⚠️ 你必須先加入一個語音頻道")
            return

        # source: 10
        channel = ctx.author.voice.channel
        vc = self._get_voice_client(ctx)
        try:
            if vc:
                if vc.channel == channel:
                    await ctx.send(f"✅ 我已經在 {channel} 了")
                else:
                    await vc.move_to(channel)
                    await ctx.send(f"✅ 已移動到 {channel}")
            else:
                await channel.connect()
                await ctx.send(f"✅ 已加入 {channel}")
        except Exception as e:
            print(f"加入頻道時發生錯誤 (Guild: {ctx.guild.id}): {e}")
            await ctx.send(f"❌ 加入頻道時發生錯誤: {e}")


    @commands.command(name="leave", aliases=['l', 'disconnect'], help="讓機器人離開語音頻道")
    async def leave(self, ctx):
        # source: 11
        """指令：離開語音頻道"""
        vc = self._get_voice_client(ctx)
        if vc:
            await self._disconnect_voice(ctx) # 使用清理函數
            await ctx.send("👋 已離開語音頻道")
        else:
            await ctx.send("⚠️ 我不在任何語音頻道中")

    @commands.command(name="play", aliases=['p'], help="播放音樂 (YouTube連結或搜尋關鍵字)")
    async def play(self, ctx, *, query: str):
        """指令：播放歌曲"""
        if ctx.author.voice is None:
            return await ctx.send("⚠️ 請先加入一個語音頻道")

        voice_channel = ctx.author.voice.channel
        vc = self._get_voice_client(ctx)

        # 如果不在頻道中，或不在使用者所在的頻道，則加入/移動
        if not vc or not vc.is_connected():
            try:
                vc = await voice_channel.connect()
            except Exception as e:
                 print(f"播放時加入頻道錯誤 (Guild: {ctx.guild.id}): {e}")
                 return await ctx.send(f"❌ 無法加入頻道 {voice_channel}: {e}")
        elif vc.channel != voice_channel:
             try:
                await vc.move_to(voice_channel)
             except Exception as e:
                 print(f"播放時移動頻道錯誤 (Guild: {ctx.guild.id}): {e}")
                 return await ctx.send(f"❌ 無法移動到頻道 {voice_channel}: {e}")


        guild_id = ctx.guild.id

        # 使用 yt-dlp 搜索或直接處理 URL
        async with ctx.typing(): # 顯示 "機器人正在輸入..."
            try:
                with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                    # 讓 yt-dlp 自動判斷是 URL 還是搜索詞
                    info = ydl.extract_info(f"ytsearch:{query}" if not query.startswith(('http:', 'https:', 'www.')) else query, download=False)

                    if 'entries' in info:
                        # 通常是搜索結果列表或播放列表的第一項
                        # source: 13
                        if not info['entries']:
                            return await ctx.send(f"🚫 找不到與 '{query}' 相關的內容。")
                        info = info['entries'][0]

                    if not info.get('url'):
                         return await ctx.send(f"🚫 無法獲取 '{info.get('title', query)}' 的播放連結。")

                    song_data = {
                        'url': info['url'], # 這是實際的音頻流 URL
                        'title': info.get('title', '未知標題'),
                        'thumbnail': info.get('thumbnail'),
                        # source: 14
                        'duration': info.get('duration'),
                        'webpage_url': info.get('webpage_url'), # 原始頁面 URL
                        'requester': ctx.author # 記錄請求者
                    }

                    # 初始化該伺服器的隊列 (如果不存在)
                    if guild_id not in self.song_queue:
                        self.song_queue[guild_id] = []

                    # 將歌曲加入隊列
                    self.song_queue[guild_id].append(song_data)
                    queue_pos = len(self.song_queue[guild_id])
                    # source: 15
                    await ctx.send(f"✅ 已將 **{song_data['title']}** 加入隊列 (位置: #{queue_pos})")

                    # 如果當前沒有在播放，則開始播放
                    if not vc.is_playing() and not vc.is_paused():
                        self._play_next_song(ctx) # 從隊列開始播放

            except yt_dlp.utils.DownloadError as e:
                 print(f"yt-dlp 下載錯誤 (Guild: {guild_id}): {e}")
                 await ctx.send(f"🚫 無法處理請求 '{query}': {e}")
            except Exception as e:
                print(f"播放指令錯誤 (Guild: {guild_id}): {e}")
                await ctx.send(f"❌ 播放時發生未預期錯誤: {e}")

    @commands.command(name="pause", help="暫停目前播放的歌曲")
    async def pause(self, ctx):
        # source: 16
        """指令：暫停播放"""
        vc = self._get_voice_client(ctx)
        if vc and vc.is_playing():
            vc.pause()
            await ctx.send("⏸️ 已暫停")
        elif vc and vc.is_paused():
             await ctx.send("⚠️ 已經是暫停狀態了")
        else:
            await ctx.send("⚠️ 目前沒有歌曲正在播放")


    @commands.command(name="resume", aliases=['r'], help="恢復播放已暫停的歌曲")
    async def resume(self, ctx):
        """指令：恢復播放"""
        vc = self._get_voice_client(ctx)
        if vc and vc.is_paused():
            vc.resume()
            # source: 17
            await ctx.send("▶️ 已恢復播放")
        elif vc and vc.is_playing():
             await ctx.send("⚠️ 歌曲正在播放中")
        else:
             await ctx.send("⚠️ 沒有已暫停的歌曲可以恢復")

    @commands.command(name="skip", aliases=['s', 'next'], help="跳過目前播放的歌曲")
    async def skip(self, ctx):
        """指令：跳過歌曲"""
        vc = self._get_voice_client(ctx)
        if vc and (vc.is_playing() or vc.is_paused()):
            # 停止當前播放，after 回調會自動觸發 _play_next_song
            vc.stop()
            await ctx.send("⏭️ 已跳過")
             # 注意：如果啟用單曲循環，跳過會重新播放同一首歌
             # 如果想讓 skip 無視單曲循環，可以在這裡臨時禁用 looping[guild_id]
             # 但目前行為是：skip 會尊重循環設定
        else:
            await ctx.send("⚠️ 目前沒有歌曲可以跳過")


    @commands.command(name="queue", aliases=['q'], help="顯示接下來要播放的歌曲隊列")
    async def queue(self, ctx):
        """指令：顯示隊列"""
        guild_id = ctx.guild.id
        if guild_id not in self.song_queue or not self.song_queue[guild_id]:
            # source: 18
            return await ctx.send("🎵 隊列目前是空的")

        embed = discord.Embed(title="🎶 歌曲隊列", color=discord.Color.blue())

        # 顯示正在播放的歌曲 (如果有的話)
        current_song = self.current_song_info.get(guild_id)
        if current_song:
             embed.add_field(name="正在播放", value=f"**{current_song['title']}** (請求者: {current_song['requester'].mention})", inline=False)
        else:
             embed.add_field(name="正在播放", value="無", inline=False)


        # 顯示隊列中的歌曲
        queue_list = ""
        max_display = 10 # 最多顯示 10 首
        for i, song in enumerate(self.song_queue[guild_id][:max_display]):
            # source: 19
            queue_list += f"`{i+1}.` **{song['title']}** (請求者: {song['requester'].mention})\n"

        if not queue_list:
            queue_list = "隊列中沒有歌曲了"
        elif len(self.song_queue[guild_id]) > max_display:
            queue_list += f"\n...還有 {len(self.song_queue[guild_id]) - max_display} 首歌"

        embed.add_field(name="待播清單", value=queue_list, inline=False)

        # 顯示循環狀態
        loop_status = "關閉"
        if self.looping.get(guild_id, False): loop_status = "單曲循環"
        qloop_status = "關閉"
        if self.queue_looping.get(guild_id, False): qloop_status = "列表循環"

        embed.set_footer(text=f"單曲循環: {loop_status} | 列表循環: {qloop_status}")

        await ctx.send(embed=embed)


    @commands.command(name="nowplaying", aliases=["np"], help="顯示目前正在播放的歌曲資訊")
    async def nowplaying(self, ctx):
        """指令：顯示當前播放歌曲"""
        guild_id = ctx.guild.id
        if guild_id not in self.current_song_info or not self.current_song_info[guild_id]:
            return await ctx.send("🔇 目前沒有播放任何歌曲")

        song = self.current_song_info[guild_id]
        embed = discord.Embed(title="💿 現在播放", description=f"**[{song['title']}]({song.get('webpage_url', song['url'])})**", color=discord.Color.green()) # 添加連結

        if song.get('thumbnail'):
            # source: 20
            embed.set_thumbnail(url=song['thumbnail'])

        if song.get('duration'):
            try:
                 # 嘗試將秒數轉換為 HH:MM:SS 或 MM:SS
                 duration_seconds = int(song['duration'])
                 minutes, seconds = divmod(duration_seconds, 60)
                 hours, minutes = divmod(minutes, 60)
                 if hours > 0:
                     duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                 else:
                     duration_str = f"{minutes:02d}:{seconds:02d}"
                 embed.add_field(name="時長", value=duration_str, inline=True)
            except:
                 embed.add_field(name="時長", value=str(song['duration']) + "秒", inline=True) # 備用方案

        if song.get('requester'):
            embed.add_field(name="請求者", value=song['requester'].mention, inline=True)

        # 添加循環狀態到頁腳
        loop_status = "關閉"
        if self.looping.get(guild_id, False): loop_status = "開啟"
        qloop_status = "關閉"
        if self.queue_looping.get(guild_id, False): qloop_status = "開啟"
        embed.set_footer(text=f"單曲循環: {loop_status} | 列表循環: {qloop_status}")


        await ctx.send(embed=embed)


    @commands.command(name="loop", help="切換單曲循環模式 (僅循環目前歌曲)")
    async def loop(self, ctx):
        """指令：切換單曲循環"""
        guild_id = ctx.guild.id
        current_loop_status = self.looping.get(guild_id, False)
        new_status = not current_loop_status
        self.looping[guild_id] = new_status

        if new_status:
            # 開啟單曲循環時，自動關閉列表循環
            if self.queue_looping.get(guild_id, False):
                 self.queue_looping[guild_id] = False
                 await ctx.send("🔁 已啟用單曲循環 (列表循環已自動關閉)")
            else:
                 await ctx.send("🔁 已啟用單曲循環")
        else:
            # source: 21
            await ctx.send("➡️ 已關閉單曲循環")


    @commands.command(name="queueloop", aliases=['qloop'], help="切換列表循環模式 (循環整個隊列)")
    async def queueloop(self, ctx):
        """指令：切換列表循環"""
        guild_id = ctx.guild.id
        current_qloop_status = self.queue_looping.get(guild_id, False)
        new_status = not current_qloop_status
        self.queue_looping[guild_id] = new_status

        if new_status:
             # 開啟列表循環時，自動關閉單曲循環
             if self.looping.get(guild_id, False):
                 self.looping[guild_id] = False
                 await ctx.send("🔁 已啟用列表循環 (單曲循環已自動關閉)")
             else:
                await ctx.send("🔁 已啟用列表循環")
        else:
            await ctx.send("➡️ 已關閉列表循環")


    @commands.command(name="volume", aliases=['vol'], help="調整音量 (0-200)")
    async def volume(self, ctx, volume: int):
        """指令：調整音量"""
        vc = self._get_voice_client(ctx)
        if not vc or not vc.source:
            return await ctx.send("⚠️ 目前沒有歌曲在播放")

        if not 0 <= volume <= 200: # 允許放大音量，但限制範圍
            return await ctx.send("⚠️ 音量必須在 0 到 200 之間")

        # source: 22
        vc.source.volume = volume / 100 # PCMVolumeTransformer 的音量是 0.0 到 2.0
        await ctx.send(f"🔊 音量已調整為 {volume}%")


    @commands.command(name="prev", aliases=['previous'], help="播放上一首歌 (需要播放歷史)")
    async def prev(self, ctx):
        """指令：播放上一首歌 (待實作)"""
        # source: 23, 24 (原邏輯已移除)
        # TODO: 實現播放歷史紀錄功能
        # 一個簡單的方法是在播放歌曲時，將 self.current_song_info 的內容存入另一個列表或字典
        # 這個 prev 指令再從歷史紀錄中取出上一首歌來播放
        await ctx.send("🚧 此功能 (`prev`) 需要播放歷史紀錄才能運作，目前尚未實作。")


    @commands.command(name="clear", help="清空歌曲隊列")
    async def clear(self, ctx):
         """指令：清空隊列"""
         guild_id = ctx.guild.id
         if guild_id in self.song_queue and self.song_queue[guild_id]:
             count = len(self.song_queue[guild_id])
             self.song_queue[guild_id] = []
             await ctx.send(f"🗑️ 已清空隊列 (共 {count} 首歌)")
         else:
             await ctx.send("⚠️ 隊列已經是空的了")

    @commands.command(name="remove", aliases=['rm'], help="移除隊列中指定位置的歌曲")
    async def remove(self, ctx, index: int):
        """指令：移除指定歌曲"""
        guild_id = ctx.guild.id
        if guild_id in self.song_queue and self.song_queue[guild_id]:
            queue = self.song_queue[guild_id]
            if 1 <= index <= len(queue):
                removed_song = queue.pop(index - 1) # 列表索引從 0 開始
                await ctx.send(f"🗑️ 已從隊列移除: **{removed_song['title']}**")
            else:
                await ctx.send(f"⚠️ 無效的位置。請輸入 1 到 {len(queue)} 之間的數字。")
        else:
            await ctx.send("⚠️ 隊列是空的，無法移除。")

    # --- 錯誤處理 ---
    @play.error
    @join.error
    @leave.error
    @pause.error
    @resume.error
    @skip.error
    @queue.error
    @nowplaying.error
    @loop.error
    @queueloop.error
    @volume.error
    @prev.error
    @clear.error
    @remove.error
    async def command_error(self, ctx, error):
        """統一處理指令執行中的錯誤"""
        if isinstance(error, commands.CommandNotFound):
            # 忽略未知指令的錯誤訊息
            return
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"⚠️ 指令缺少必要參數：`{error.param.name}`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"⚠️ 無效的參數類型：{error}")
        elif isinstance(error, commands.CheckFailure):
            await ctx.send("🚫 你沒有權限執行此指令。")
        elif isinstance(error, commands.CommandInvokeError):
            original = error.original
            print(f'指令調用錯誤 (Guild: {ctx.guild.id}, Command: {ctx.command.qualified_name}): {original}')
            await ctx.send(f"❌ 執行指令時發生內部錯誤: {original}")
        else:
            # 其他未捕捉的錯誤
            print(f'未處理的錯誤 (Guild: {ctx.guild.id}, Command: {ctx.command.qualified_name}): {error}')
            await ctx.send(f"❌ 發生未預期的錯誤: {error}")


# Cog 的 setup 函數，用於載入 Cog
# async def setup(bot):
#     await bot.add_cog(MusicCog(bot))