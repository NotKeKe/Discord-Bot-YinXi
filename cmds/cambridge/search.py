import httpx
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from collections import defaultdict
import re

from .config import *

# https://dictionary.cambridge.org/dictionary/english-chinese-traditional/abc

async def search(keyword: str, client: httpx.AsyncClient) -> list:
    url = urljoin(SEARCH_URL, keyword)

    resp = await client.get(url)
    if resp.status_code != 200: return []

    soup = BeautifulSoup(resp.text, 'html.parser')
    divs = soup.find_all('div', class_ = Classes.DEF_BLOCK) or soup.find_all('div', class_ = Classes.DEF_BLOCK_2)

    infos = []

    for div in divs:
        info = defaultdict(list)

        h3 = div.find('h3')
        h3_text = ' '.join(h3.stripped_strings if h3 else [])
        info['word'] = h3_text.strip() # type: ignore
        
        meaning_div = div.find_all('span', class_ = Classes.TRANSLATION)

        for meaning in meaning_div:
            clean_text = meaning.text if meaning else ''
            clean_texts = re.split(r',|;|\||；|，', clean_text.strip())
            info['meaning'].extend(clean_texts)
            
        # 找例句
        example_sentence_div = div.find_all('div', class_ = Classes.EXMAPLE_SENTENCE_div)
        for sentence in example_sentence_div:
            eg = sentence.find('span', class_ = Classes.EG_SENTENCE) # 英文
            translate = sentence.find('span', class_ = Classes.TRANSLATION_SENTENCE) # 中文

            eg_clean_text = eg.text if eg else ''
            translate_clean_text = translate.text if translate else ''

            info['examples'].append({
                'eg': eg_clean_text.strip(),
                'translate': translate_clean_text.strip()
            })

        infos.append(info)
            
    return infos