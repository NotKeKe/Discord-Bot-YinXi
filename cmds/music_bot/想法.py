import discord
from discord.ext import commands
import asyncio

from core.functions import read_json, write_json, create_basic_embed


'''
personal list 參照例子
'''
personal_list = {
    'member.id': [
        {
            'audio_url': 132, 
            'title': 123, 
            'length': 123, 
            'thumbnail': 123, 
            'video_url': 123
        }
    ]
}

# 代表全部歌曲
'''
queues 參照例子
'''
queues = {
    'ctx.guild.id': [
        {
            'audio_url': 111, 
            'title': 111, 
            'length': 111, 
            'thumbnail': 111, 
            'video_url': 111,
        }
    ]
}
# 將for迴圈放在function裡面給ctx.typing
# async with ctx.typing():
#     # 使用 asyncio 來避免阻塞
#     loop = asyncio.get_event_loop()
#     options = await loop.run_in_executor(executor=None, func = lambda: FUNCTION_NAME)


'''
大約是一個for迴圈給user在裡面循環 用current index來取得正在播放哪一項
(即原本的queues跟current_playing結合)
跟上面註解的ctx.typing結合
'''
def process_queue():
    global current_index
    for index, item in enumerate(queues['ctx.guild.id']):
        current_index = index
        audio_url = item['audio_url']
        title = item['title']
        length = item['length']
        thumbnail = item['thumbnail']
        video_url = item['video_url']
        
        # 在這裡執行您需要的操作
        print(f"正在處理第 {current_index + 1} 項: Audio URL: {audio_url}, Title: {title}, Length: {length}, Thumbnail: {thumbnail}, Video URL: {video_url}")
        
        # 暫停 5 秒
        # await asyncio.sleep(5)


looping = ['ctx.guild.id1', 'ctx.guild.id2']
if 'ctx.guild.id' in looping:
    pass

# 使用前一首，looping，以及預設情況要用到current_playing_index
current_playing_index = {
    'ctx.guild.id1': 1,
    'ctx.guild.id2': 3
}

def play(bot, ctx, voice_client, link):
    voice_client.play(discord.FFmpegPCMAudio(link, **ffmpeg_options), after=lambda e: asyncio.run_coroutine_threadsafe(play_next(bot, ctx), bot.loop))

[
    [
        {
            "audio_url": "https://rr3---sn-ipoxu-un5es.googlevideo.com/videoplayback?expire=1738328243&ei=U3ScZ5GFC9Xq7OsPs5eToQ4&ip=1.162.59.125&id=o-APo5j0LorE8UUTw2zhW-c2IBEnaXBuo2jzPxTDgnjg5W&itag=140&source=youtube&requiressl=yes&xpc=EgVo2aDSNQ%3D%3D&met=1738306643%2C&mh=ea&mm=31%2C29&mn=sn-ipoxu-un5es%2Csn-un57enez&ms=au%2Crdu&mv=m&mvi=3&pcm2cms=yes&pl=24&rms=au%2Cau&initcwndbps=3532500&bui=AY2Et-MFaxnFqLM5xjT6u5WnrMVpbDRzvNudifVMgg_Np92H5_qlV4Som7B7r5C11UwuNeQOEgawHqns&spc=9kzgDdRlT11brle6RuVs1eZMcnfS0Ji6BZT3pZC-weCoMWPj8gztudo6ZR5rGlw&vprv=1&svpuc=1&mime=audio%2Fmp4&ns=iv8HC6BNCARZcF-eD4N4_ZkQ&rqh=1&gir=yes&clen=2504553&dur=154.691&lmt=1737953474818569&mt=1738306145&fvip=4&keepalive=yes&fexp=51326932%2C51355912%2C51371294&c=WEB&sefc=1&txp=5532534&n=OAlSiIWcNQeQ2A&sparams=expire%2Cei%2Cip%2Cid%2Citag%2Csource%2Crequiressl%2Cxpc%2Cbui%2Cspc%2Cvprv%2Csvpuc%2Cmime%2Cns%2Crqh%2Cgir%2Cclen%2Cdur%2Clmt&lsparams=met%2Cmh%2Cmm%2Cmn%2Cms%2Cmv%2Cmvi%2Cpcm2cms%2Cpl%2Crms%2Cinitcwndbps&lsig=AGluJ3MwRQIgTRcP2KaXi2UO6BttpbJRjf0mhRnVy4jf7G_KG5DmCOgCIQDT6cU6cWSNM4ds5c3g5NVxHesprV9-x1gRD8mc4wMOtg%3D%3D&pot=Mngd5dioCSfpzR3ZgUSnKFa_MV_lEjezHTcGWrNxXjBsAJFWDocmbKa92jOP1Z5oN4FI4cp3o2VHtKhyDEvanrXM45hZJpOWA0VuD-wrtUuk3tOsX30dZPeaHVqSdhFIk-2pbpzR7G0u7Aa4t8roJYT7vjnQpHlrXYY%3D&sig=AJfQdSswRAIgO4H31FQC7oqkxTnhQctYz2MyQAVooZmQ6buwMBBH_hMCIBGzWJHMjWEpxlYssAl7c2AQLOS0lA88nckFlneLWufb",
            "title": "混沌ブギ / jon-YAKITORY, 初音ミク -Konton Boogie / jon-YAKITORY, Hatsune Miku-",
            "length": "0:02:35",
            "thumbnail": "https://i.ytimg.com/vi/1Swg-aBO9eY/maxresdefault.jpg",
            "video_url": "https://youtube.com/watch?v=1Swg-aBO9eY"
        },
        {
            "audio_url": "https://rr2---sn-ipoxu-un5es.googlevideo.com/videoplayback?expire=1738328274&ei=cnScZ8DWNu7Ms8IPrPeimQ4&ip=1.162.59.125&id=o-AJ6dsUkQ8dopW1dnTu72U56UCVJgXaaGhnJ7aRSz2ftu&itag=140&source=youtube&requiressl=yes&xpc=EgVo2aDSNQ%3D%3D&met=1738306674%2C&mh=6V&mm=31%2C29&mn=sn-ipoxu-un5es%2Csn-un57enez&ms=au%2Crdu&mv=m&mvi=2&pl=24&rms=au%2Cau&initcwndbps=3132500&bui=AY2Et-Oh0ojF4fb8v0mhR0QVBsLQDKJrwdCDXisrXL-utU_uGKPdmqdwmkO8FiPFRi-tQPbAim99pUbn&spc=9kzgDXRSCqKymj7o2qYrKEu6WE6kyd89XHiEzzwWTgXR4QXeRDuwHuibZqvlOBs&vprv=1&svpuc=1&mime=audio%2Fmp4&ns=VmbaDMjoDot7FNetV-qkFysQ&rqh=1&gir=yes&clen=3724559&dur=230.086&lmt=1726962621867722&mt=1738306388&fvip=1&keepalive=yes&fexp=51326932%2C51355912%2C51371294&c=WEB&sefc=1&txp=5532434&n=QIhChrpBEI6-lw&sparams=expire%2Cei%2Cip%2Cid%2Citag%2Csource%2Crequiressl%2Cxpc%2Cbui%2Cspc%2Cvprv%2Csvpuc%2Cmime%2Cns%2Crqh%2Cgir%2Cclen%2Cdur%2Clmt&lsparams=met%2Cmh%2Cmm%2Cmn%2Cms%2Cmv%2Cmvi%2Cpl%2Crms%2Cinitcwndbps&lsig=AGluJ3MwRAIgf-4RZh9ZNZ_e-yR0QBX0deXMdVK2uKHni-vw63n3JygCIGaDh_EZJCUWz1qEW149B9AU_GQzFfUQXheE0neQa_vK&pot=MngiHXKFRYNO_SIhDbV17jZooNY2_QfLlRGw0TbVMyVeZt5-3OmFqUaIEn4bAYWcBQbJVQquirT_N1VBIkBzTnDmnD9ykpfyeUZPE0sKZ11Hlq4mAJTLosrzzEsIYDBXI6mbMDtjgBPcDsVQqHrS1zQ0dyK_XO4XWAo%3D&sig=AJfQdSswRAIgdKCiQH8z8Bm722MK8pm4HfVtBA1fL7dh8P13xAknzV0CIGVXaz7KCSovcAPxk2zRsu3vew1u8lX2znxPSXRhMXgk",
            "title": "WiFi歪歪 -  就忘了吧 (完整版)「在那些和你錯開的時間裡 我騙過我自己 以為能忘了你」【動態歌詞】♪",
            "length": "0:03:50",
            "thumbnail": "https://i.ytimg.com/vi/BuNrMHlad80/maxresdefault.jpg",
            "video_url": "https://youtube.com/watch?v=BuNrMHlad80"
        }
    ],
    [
        {
            'awfkwoapflk': 'ajfioamfklwf'
        }
    ]
]