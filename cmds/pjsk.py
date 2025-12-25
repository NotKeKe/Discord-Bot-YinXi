import discord
from discord import app_commands, Interaction
from discord.app_commands import Choice
from discord.ext import commands, tasks
import aiohttp
import logging
from collections import defaultdict
from typing import Any
from pymongo import UpdateOne
from textwrap import dedent
from datetime import datetime
import asyncio
from motor.motor_asyncio import AsyncIOMotorCursor
import re

from core.mongodb import MongoDB_DB
from core.translator import locale_str, load_translated
from core.functions import create_basic_embed, UnixToReadable

logger = logging.getLogger(__name__)

sekai_best_url = 'https://sekai.best/'
sekai_best_icon_url = 'https://avatars.githubusercontent.com/u/72262118?s=48&v=4'

ALL_DIFFS = ["easy", "normal", "hard", "expert", "master", "append"]

db = MongoDB_DB.pjsk
collection = MongoDB_DB.pjsk['songs']

async def song_autocomplete(inter: Interaction, current: str) -> list[Choice[str]]:
    await collection.find({
        '$or': [
            {"songName": {"$regex": current, "$options": "i"}},
            {"lyricist": {"$regex": current, "$options": "i"}},
            {"composer": {"$regex": current, "$options": "i"}},
            {"arranger": {"$regex": current, "$options": "i"}}
        ]
    })

def get_descrip_of_info_embed(item: dict, descrips: list, descrip_template: str):
    """
    Args:
        item (dict): A item including song_name, difficulty...
        descrips (list): 最終用於 embed 內的描述 list
        descrip_template (str): 轉換單個 item 的 str template
    """    
    song_name = item.get('songName')
    difficulty = '\n'.join([
        f"- {diff} | Lv.{value.get('level')} | 🎵 {value.get('noteCount')}"
        for diff, value in item.get('musicDifficulty').items()
    ])
    image_url = item.get('imageUrl')
    video_url = item.get('musicVideoUrl')
    charts_url = '\n'.join([f'* [{diff}]({val})' for diff, val in item.get('musicChartUrl').items()])
    music_tag = '\n'.join(item.get('musicTag'))
    publish_at = UnixToReadable(item.get('publishAt', 0))
    lyricist = item.get('lyricist')
    composer = item.get('composer')
    arranger = item.get('arranger')

    descrips.append(descrip_template.format(
        song_name=song_name,
        difficulty=difficulty,
        image_url=image_url,
        video_url=video_url,
        charts_url=charts_url,
        music_tag=music_tag,
        publish_at=publish_at,
        lyricist=lyricist,
        composer=composer,
        arranger=arranger,
    ))

async def create_info_embed(ctx: commands.Context, cursor: AsyncIOMotorCursor):
    '''
    cursor: collection.find()
    '''
    embed = create_basic_embed()
    descrips = []

    '''i18n'''
    eb_text = load_translated(
        (await ctx.interaction.translate('embed_pjsk_global_full_info')) 
        if ctx.interaction else 
        (await ctx.bot.tree.translator.get_translate('embed_pjsk_global_full_info', ctx.guild.preferred_locale.value))
    )[0]
    footer = eb_text.get('footer')
    descrip = eb_text.get('description')
    ''''''

    async for item in cursor:
        get_descrip_of_info_embed(item, descrips, descrip)
        
    embed.description = '\n\n'.join(descrips)
    embed.set_author(name='sekai.best', url=sekai_best_url, icon_url=sekai_best_icon_url)
    embed.set_footer(text=footer)

    return embed

class PJSK(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.db = db
        self.collection = collection
        self.send_channels_collection = self.db['notif_channels']

    async def cog_load(self):
        print(f'已載入「{__name__}」')
        self.update_pjsk_songs.start()

    async def cog_unload(self):
        self.update_pjsk_songs.cancel()

    @commands.hybrid_command(name=locale_str('pjsk_new_song'), description=locale_str('pjsk_new_song'))
    async def new_song(self, ctx: commands.Context):
        await ctx.defer()

        embed = await create_info_embed(ctx, collection.find().sort('publishAt', -1).limit(3))
        await ctx.send(embed=embed)

    @commands.hybrid_command(name=locale_str('pjsk_search_song'), description=locale_str('pjsk_search_song'))
    @app_commands.describe(
        name=locale_str('pjsk_search_song_name'), 
        num=locale_str('pjsk_search_song_num'), 
        level=locale_str('pjsk_search_song_level'), 
        combo=locale_str('pjsk_search_song_combo')
    )
    async def search_song(self, ctx: commands.Context, name: str = None, num: int = 5, level: int = None, combo: int = None):
        if not (name or level or combo): return await ctx.send(await ctx.interaction.translate('send_pjsk_search_song_no_param'))
        await ctx.defer()
        
        '''Copilot(with GPT5) did this'''
        # 基本條件集合
        name = re.escape(name) if name else ""
        text_conds = []
        if name:
            text_conds = [
                {"songName": {"$regex": name, "$options": "i"}},
                {"lyricist": {"$regex": name, "$options": "i"}},
                {"composer": {"$regex": name, "$options": "i"}},
                {"arranger": {"$regex": name, "$options": "i"}}
            ]
        
        level_conds = [
            {f"musicDifficulty.{diff}.level": level}
            for diff in ALL_DIFFS if level is not None
        ]
        combo_conds = [
            {f"musicDifficulty.{diff}.noteCount": combo}
            for diff in ALL_DIFFS if combo is not None
        ]
        
        # 根據 match_all 決定用 AND 還是 OR
        if sum(bool(x) for x in (name, level, combo)) >= 2:
            # 必須同時符合 → 每個種類的條件要包成一組 AND
            conds = []
            if text_conds:
                conds.append({"$or": text_conds})  # 名稱類只要其中一欄命中即可
            if level_conds:
                conds.append({"$or": level_conds})
            if combo_conds:
                conds.append({"$or": combo_conds})
            match_stage = {"$and": conds}
        else:
            # 任一條件符合
            match_stage = {"$or": text_conds + level_conds + combo_conds}

        pipeline = [
            {"$match": match_stage},
            {
                "$addFields": {
                    "_score": {
                        "$cond": [
                            {"$regexMatch": {"input": "$songName", "regex": name, "options": "i"}},
                            1, 0
                        ]
                    }
                }
            },
            {"$sort": {"_score": -1}},
            {"$limit": num}
        ]

        cursor = self.collection.aggregate(pipeline)
        ''''''
        try:
            if num == 1:
                eb = await create_info_embed(ctx, cursor)
            else:
                '''i18n'''
                eb_text = load_translated(
                    (await ctx.interaction.translate('embed_pjsk_search_song_short_info')) 
                    if ctx.interaction else 
                    (await self.bot.tree.translator.get_translate('embed_pjsk_search_song_short_info', ctx.guild.preferred_locale.value))
                )[0]
                footer = eb_text.get('footer')
                descrip = eb_text.get('description')
                ''''''

                eb = create_basic_embed()
                eb.description = '\n\n'.join([descrip.format(
                    song_name = item.get('songName'),
                    difficulty = '\n'.join([
                        f"- {diff} | Lv.{value.get('level')} | 🎵 {value.get('noteCount')}"
                        for diff, value in item.get('musicDifficulty').items()
                    ]),
                    publish_at = UnixToReadable(item.get('publishAt', 0)),
                    lyricist = item.get('lyricist'),
                    composer = item.get('composer'),
                    arranger = item.get('arranger')
                ) async for item in cursor])

                eb.set_footer(text=footer)
        except:
            logger.error('error:', exc_info=True)

        await ctx.send(embed=eb)

    @commands.hybrid_command(name=locale_str('pjsk_new_song_notify'), description=locale_str('pjsk_new_song_notify'))
    @app_commands.checks.has_permissions(manage_channels=True)
    async def pjsk_new_song_notify(self, ctx: commands.Context):
        async with ctx.typing():
            is_in_col = await self.send_channels_collection.find_one({'channelID': ctx.channel.id})

            if not is_in_col:
                await self.send_channels_collection.insert_one({'channelID': ctx.channel.id, 'createAt': datetime.now().timestamp()})
                await ctx.send(await ctx.interaction.translate('send_pjsk_new_song_notify_opened'))
                return

            button_check = discord.ui.Button(label='Yes', style=discord.ButtonStyle.blurple, emoji='✅')
            button_refuse = discord.ui.Button(label='No', style=discord.ButtonStyle.blurple, emoji='❌')

            async def button_check_callback(inter: Interaction):
                await inter.response.defer()
                msg = inter.message
                
                await self.send_channels_collection.find_one_and_delete({'channelID': ctx.channel.id})

                await inter.followup.send(await inter.translate('send_pjsk_new_song_notify_delete_success'), ephemeral=True)
                await msg.edit(view=None)
            async def button_refuse_callback(inter: Interaction):
                await inter.response.defer()
                msg = inter.message
                await inter.followup.send(await inter.translate('send_pjsk_new_song_notify_delete_cancel'), ephemeral=True)
                await msg.edit(view=None)


            button_check.callback = button_check_callback
            button_refuse.callback = button_refuse_callback

            view = discord.ui.View()
            view.add_item(button_check)
            view.add_item(button_refuse)

            '''i18n'''
            eb = load_translated(await ctx.interaction.translate('embed_pjsk_new_song_notify_delete'))[0]
            eb_title = eb.get('title')
            ''''''

            eb = create_basic_embed('❓' + eb_title)
            
            await ctx.send(embed=eb, view=view)

    @tasks.loop(hours=1)
    async def update_pjsk_songs(self):
        updated = []
        '''有更新的數據'''
        results = []
        '''要傳送到 dc channel 的數據'''

        async with aiohttp.ClientSession() as session:
            async with session.get('https://sekai-world.github.io/sekai-master-db-diff/musics.json') as resp:
                musics: list[dict[str, Any]] = await resp.json()
                musics.sort(key=lambda x: x.get('publishedAt'))

            async with session.get('https://sekai-world.github.io/sekai-master-db-diff/musicDifficulties.json') as resp:
                music_difficulties = await resp.json()

            async with session.get('https://sekai-world.github.io/sekai-master-db-diff/musicOriginals.json') as resp:
                music_video_urls = {item["musicId"]: item for item in (await resp.json())}

            async with session.get('https://sekai-world.github.io/sekai-master-db-diff/musicTags.json') as resp:
                music_tags: dict[str, list[str]] = defaultdict(list)
                for item in (await resp.json()):
                    music_tags[item["musicId"]].append(item.get('musicTag'))

        for music in musics:
            # 歌曲id, 名稱
            music_id = music.get('id')

            song_name = music.get('title')
            publish_at: int = music.get('publishedAt') # type: ignore
            music_difficulty = { # {append: {lvl: 32, noteCount: 1131}]
                music_diff.get('musicDifficulty'): {
                    'level': music_diff.get('playLevel'), 
                    'noteCount': music_diff.get('totalNoteCount')
                }
                for music_diff in music_difficulties if music_diff.get('musicId') == music_id
            }
            music_video_url: str = music_video_urls.get(music_id, {}).get('videoLink')
            music_chart_url = { # 譜面連結
                diff: f"https://storage.sekai.best/sekai-music-charts/jp/{str(music_id).zfill(4)}/{diff}.png"
                for diff in music_difficulty.keys()
            }
            music_tag: list[str] = music_tags.get(music_id) # type: ignore

            # 歌曲作詞, 作曲, 編曲
            lyricist = music.get('lyricist')
            composer = music.get('composer')
            arranger = music.get('arranger')

            # 為了定位圖片url
            image_assetbundle_name = music.get('assetbundleName')
            image_url = f"https://storage.sekai.best/sekai-jp-assets/music/jacket/{image_assetbundle_name}/{image_assetbundle_name}.webp"

            item = {
                'musicId': music_id, # 歌曲ID
                'songName': song_name, # 歌曲名稱
                'musicDifficulty': music_difficulty, # 歌曲難度: dict[難度, dict[lvl | noteCount, int]]
                'imageUrl': image_url, # 封面連結
                'musicVideoUrl': music_video_url, # 歌曲影片連結 (原唱)
                'musicChartUrl': music_chart_url, # 歌曲譜面: dict[難度, url]
                'publishAt': publish_at, # 歌曲在遊戲中的發布時間: jp timestamp, int
                
                'musicTag': music_tag, # 歌曲標籤: list[樂團]'
                'lyricist': lyricist, # 作詞
                'composer': composer, # 作曲
                'arranger': arranger, # 編曲
            }

            find_one_result = await self.collection.find_one({'musicId': music_id})

            if not (find_one_result):
                results.append(item)

            if find_one_result and find_one_result | {'_id': ''} == item | {'_id': ''}: return
            updated.append(item)
        
        if not results: return
        else: # 有新歌曲才發送 channel 通知
            async for item in self.send_channels_collection.find():
                channelID: int = item.get('channelID')
                channel = self.bot.get_channel(channelID)

                lang = channel.guild.preferred_locale.value if hasattr(channel, 'guild') and channel.guild else None # type: ignore

                '''i18n'''
                eb_text = load_translated(await self.bot.tree.translator.get_translate('embed_pjsk_global_full_info', lang))[0] # type: ignore
                footer = eb_text.get('footer')
                descrip = eb_text.get('description')
                ''''''

                for r in results:
                    send_descrip = []
                    get_descrip_of_info_embed(r, send_descrip, descrip) # 可能遇到語言不同的問題 descrip 就會不一樣

                    embed = create_basic_embed()

                    embed.description = '\n\n'.join(send_descrip)
                    embed.set_author(name='sekai.best', url=sekai_best_url, icon_url=sekai_best_icon_url)
                    embed.set_footer(text=footer)

                    await channel.send(embed=embed) # type: ignore
        
        
        await self.collection.bulk_write([
            UpdateOne({"musicId": r.get('musicId')}, {"$set": r}, upsert=True) 
            for r in updated if r.get('musicId')
        ])
        await self.collection.update_one({'type': 'TOP_STATS'}, {'$set': {'updateAt': datetime.now().timestamp()}}, upsert=True)
        logger.info(f'Updated pjsk data with {len(updated)} results')

    @update_pjsk_songs.before_loop
    async def update_pjsk_songs_before_loop(self):
        await self.bot.wait_until_ready()
        last_update_data = await self.collection.find_one({'type': 'TOP_STATS'})
        if last_update_data:
            ts = last_update_data.get('updateAt', 0)
            if datetime.now().timestamp() - ts < 60*60:
                await asyncio.sleep(60*60 - (datetime.now().timestamp() - ts))
    

async def setup(bot):
    await bot.add_cog(PJSK(bot))