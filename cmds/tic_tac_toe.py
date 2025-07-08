"""雖然這百分之99.8都是Copliot寫的，但我讓他生成出這段正常的程式也花了很久時間:sob:"""

import discord
from discord.ext import commands

from core.translator import locale_str

class TicTacToeGame:
    def __init__(self):
        self.board = [[":new_moon:" for _ in range(3)] for _ in range(3)]
        self.moves = {":x:": [], ":blue_circle:": []}
        self.previous_moves = {":x:": [], ":blue_circle:": []}
        self.current_player = ":x:"

    def format_board(self):
        return "\n".join([" | ".join(row) for row in self.board])

    def check_winner(self):
        for row in range(3):
            if self.board[row][0] == self.board[row][1] == self.board[row][2] and self.board[row][0] != ":new_moon:":
                return self.board[row][0]
        for col in range(3):
            if self.board[0][col] == self.board[1][col] == self.board[2][col] and self.board[0][col] != ":new_moon:":
                return self.board[0][col]
        if self.board[0][0] == self.board[1][1] == self.board[2][2] and self.board[0][0] != ":new_moon:":
            return self.board[0][0]
        if self.board[0][2] == self.board[1][1] == self.board[2][0] and self.board[0][2] != ":new_moon:":
            return self.board[0][2]
        return None

class TicTacToe(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')

    @commands.hybrid_command(name=locale_str('tictactoe'), description=locale_str('tictactoe_description'))
    async def start_game(self, ctx: commands.Context):
        '''
        [圈圈叉叉 或是 [tictactoe
        跟別人玩圈圈叉叉
        基本上全部人都能按
        '''
        self.games[ctx.channel.id] = TicTacToeGame()
        game = self.games[ctx.channel.id]
        '''i18n'''
        i18n_data = await ctx.interaction.translate('embed_tictactoe_game')
        i18n_data = i18n_data[0]
        ''''''
        embed = discord.Embed(title=i18n_data['title'], description=game.format_board(), color=discord.Color.blue())
        embed.add_field(name=i18n_data['field'][0]['name'], value=game.current_player, inline=i18n_data['field'][0].get('inline', True))
        await ctx.send(embed=embed, view=await self.create_view(ctx, ctx.channel.id))

    async def create_view(self, ctx: commands.Context, channel_id: int):
        view = discord.ui.View()
        
        '''i18n'''
        button_labels = await ctx.interaction.translate('button_tictactoe_labels')
        button_labels = button_labels[0]
        ''''''

        positions = [
            (button_labels['top_left'], 0, 0),
            (button_labels['top_center'], 0, 1),
            (button_labels['top_right'], 0, 2),
            (button_labels['middle_left'], 1, 0),
            (button_labels['middle_center'], 1, 1),
            (button_labels['middle_right'], 1, 2),
            (button_labels['bottom_left'], 2, 0),
            (button_labels['bottom_center'], 2, 1),
            (button_labels['bottom_right'], 2, 2)
        ]
        for label, row, col in positions:
            view.add_item(discord.ui.Button(label=label, style=discord.ButtonStyle.primary, custom_id=f"{channel_id}-{row}-{col}"))
        return view

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        try:
            if interaction.data["component_type"] != 2:  # 確保是按鈕互動
                return

            custom_id = interaction.data["custom_id"]
            channel_id, row, col = map(int, custom_id.split("-"))

            if channel_id not in self.games:
                await interaction.response.send_message(await interaction.translate('send_tictactoe_no_game'), ephemeral=True)
                return

            game = self.games[channel_id]

            if game.board[row][col] == ":new_moon:":
                # 先替換對方最早的標記
                if game.current_player == ":x:" and len(game.moves[":blue_circle:"]) > 2:
                    oldest_move = game.moves[":blue_circle:"].pop(0)
                    game.board[oldest_move[0]][oldest_move[1]] = ":black_circle:"
                    game.previous_moves[":blue_circle:"].append(oldest_move)
                elif game.current_player == ":blue_circle:" and len(game.moves[":x:"]) > 2:
                    oldest_move = game.moves[":x:"].pop(0)
                    game.board[oldest_move[0]][oldest_move[1]] = ":heavy_multiplication_x:"
                    game.previous_moves[":x:"].append(oldest_move)

                # 放置當前玩家的標記
                game.board[row][col] = f"  {game.current_player}  "
                game.moves[game.current_player].append((row, col))

                # 將原本已經修改過的標記改回 :new_moon:
                if game.current_player == ":x:" and game.previous_moves[":x:"]:
                    previous_move = game.previous_moves[":x:"].pop(0)
                    game.board[previous_move[0]][previous_move[1]] = ":new_moon:"
                elif game.current_player == ":blue_circle:" and game.previous_moves[":blue_circle:"]:
                    previous_move = game.previous_moves[":blue_circle:"].pop(0)
                    game.board[previous_move[0]][previous_move[1]] = ":new_moon:"

                # 檢查是否有玩家獲勝
                winner = game.check_winner()
                if winner:
                    '''i18n'''
                    i18n_data = await interaction.translate('embed_tictactoe_game')
                    i18n_data = i18n_data[0]
                    ''''''
                    embed = discord.Embed(title=i18n_data['title'], description=i18n_data['winner_description'].format(winner=winner) + f"\n\n{game.format_board()}", color=discord.Color.green())
                    await interaction.response.edit_message(embed=embed, view=None)
                    self.games.pop(channel_id)
                else:
                    game.current_player = ":blue_circle:" if game.current_player == ":x:" else ":x:"
                    '''i18n'''
                    i18n_data = await interaction.translate('embed_tictactoe_game')
                    i18n_data = i18n_data[0]
                    ''''''
                    embed = discord.Embed(title=i18n_data['title'], description=game.format_board(), color=discord.Color.blue())
                    embed.add_field(name=i18n_data['field'][0]['name'], value=game.current_player, inline=i18n_data['field'][0].get('inline', True))
                    ctx = await self.bot.get_context(interaction)
                    await interaction.response.edit_message(embed=embed, view=await self.create_view(ctx, channel_id))
            else:
                await interaction.response.send_message(await interaction.translate('send_tictactoe_position_taken'), ephemeral=True)
        except: pass

async def setup(bot):
    await bot.add_cog(TicTacToe(bot))