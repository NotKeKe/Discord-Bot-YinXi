import discord
from discord.ext import commands

# _handle_ephemeral_for_context 輔助函式保持不變
def _handle_ephemeral_for_context(kwargs: dict):
    if kwargs.pop('ephemeral', False):
        kwargs['delete_after'] = 5
        original_content = kwargs.get('content', '')
        note = " "
        kwargs['content'] = note + original_content
    return kwargs


# --- 修正後的 MockFollowup ---
class MockFollowup:
    def __init__(self, ctx: commands.Context):
        self._ctx = ctx

    async def send(self, *args, **kwargs) -> discord.Message:
        """
        模仿 followup.send()。
        """
        # 步驟 1: 處理 ephemeral 參數 (來自上一個修正)
        # processed_kwargs = _handle_ephemeral_for_context(kwargs)
        processed_kwargs = kwargs
        processed_kwargs.pop('ephemeral', False)
        
        # 步驟 2: 【關鍵修正】安全地移除 wait 參數，因為我們的模擬行為已經是 "wait=True"
        processed_kwargs.pop('wait', None)
        
        # 步驟 3: 呼叫底層函式
        return await self._ctx.channel.send(*args, **processed_kwargs)

# --- 修正後的 MockInteractionResponse ---
class MockInteractionResponse:
    def __init__(self, ctx: commands.Context):
        self._ctx = ctx
        self._sent = True
        
    def is_done(self) -> bool:
        return self._sent

    async def send_message(self, *args, **kwargs):
        if self.is_done():
            # 如果已經回應過，應由 followup 處理。
            # 這裡我們直接呼叫 followup 的邏輯。
            followup = MockFollowup(self._ctx)
            await followup.send(*args, **kwargs)
            return

        """
        【關鍵修正】: 在發送前處理 ephemeral 參數。
        """
        # processed_kwargs = _handle_ephemeral_for_context(kwargs)
        kwargs.pop('ephemeral', False)
        processed_kwargs = kwargs

        msg = await self._ctx.channel.send(*args, **processed_kwargs)
        return msg

    async def defer(self, *, thinking: bool = True, ephemeral: bool = False):
        if self.is_done():
            return

        # 如果 defer 本身要求是 ephemeral，我們也用自動刪除的訊息來提示
        # if ephemeral:
        #     await self._ctx.channel.send("(正在處理，此為臨時訊息...)", delete_after=3)
        
        await self._ctx.channel.typing()
        self._sent = True


# 最終的 MockInteraction
class MockInteraction:
    def __init__(self, ctx: commands.Context):
        # 【關鍵修正】: 將 ctx 物件掛載到 mock interaction 上，以便需要時能存取
        # 這對 `InteractionResponded` 錯誤等地方可能有用
        # 同時，這也是 discord.py 內部判斷的依據
        self._ctx = ctx 
        ctx.interaction = self # 將 mock 物件掛載回 ctx，使其更逼真

        self.response = MockInteractionResponse(ctx)
        self.followup = MockFollowup(ctx)
        
        # 複製常用屬性
        self.user = ctx.author
        self.guild = ctx.guild
        self.channel = ctx.channel
        self.client = ctx.bot
        self.bot = ctx.bot
        ctx.guild.preferred_locale
        self.locale: discord.Locale = ctx.guild.preferred_locale or discord.Locale.taiwan_chinese # 或是從伺服器設定讀取

    def is_expired(self) -> bool:
        """
        模仿真實的 is_expired() 方法。
        由於此互動是基於不會過期的 Context 創建的，
        所以它永遠不會過期。
        """
        return False

    async def translate(self, string: str, lang_code: str = None):
        return await self.bot.tree.translator.get_translate(string, lang_code, self._ctx)