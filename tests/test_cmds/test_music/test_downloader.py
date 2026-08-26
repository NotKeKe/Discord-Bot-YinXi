import asyncio
import sys

import pytest

async def _import_modules():
    # utils.py 會在 import 時建立 MyPriorityQueue 並呼叫 asyncio.create_task
    # 因此必須在 running event loop 內 import
    from cmds.music_bot.play4.downloader import extract_info, extract_info_pytube, extract_info_yt_dlp
    return extract_info, extract_info_pytube, extract_info_yt_dlp

extract_info, extract_info_pytube, extract_info_yt_dlp = asyncio.run(_import_modules())

TEST_URL = 'https://youtu.be/jNQXAC9IVRw'


def test_extract_info_yt_dlp():
    result = extract_info_yt_dlp(TEST_URL)

    assert result['audio_url']
    assert result['thumbnail_url'].startswith('http')
    assert result['title']
    assert result['duration'] > 0
    assert isinstance(result['subtitles'], dict)


def test_extract_info_pytube():
    result = extract_info_pytube(TEST_URL)

    assert result['audio_url']
    assert result['thumbnail_url'].startswith('http')
    assert result['title']
    assert result['duration'] > 0
    assert isinstance(result['subtitles'], dict)


@pytest.mark.skipif(
    sys.platform == 'win32',
    reason='extract_info 使用 ProcessPoolExecutor，在 Windows spawn 的 child process 會重新 import utils.py，'
           '其 module-level 的 MyPriorityQueue() 需要 running event loop，導致 BrokenProcessPool',
)
@pytest.mark.asyncio
async def test_extract_info():
    result = await extract_info(TEST_URL)

    assert result['audio_url']
    assert result['thumbnail_url'].startswith('http')
    assert result['title']
    assert result['duration'] > 0
    assert isinstance(result['subtitles'], dict)