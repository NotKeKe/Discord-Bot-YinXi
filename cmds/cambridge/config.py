from urllib.parse import urljoin

BASE_URL = 'https://dictionary.cambridge.org'
SEARCH_URL = urljoin(BASE_URL, 'dictionary/english-chinese-traditional/')

USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.94 Safari/537.36'

class Selectors:
    WORD = 'span.hw.dhw'
    POS = 'span.pos.dpos' # 詞性
    DEF_BLOCK = 'div.pr.dsense'

class Classes:
    WORD = 'hw'
    POS = 'pos'
    DEF_BLOCK = 'pr dsense'
    DEF_BLOCK_2 = 'pr dsense dsense-noh'
    TRANSLATION = 'trans dtrans dtrans-se break-cj'
    EXMAPLE_SENTENCE_div = 'examp dexamp' # a div
    EG_SENTENCE = 'eg deg'
    TRANSLATION_SENTENCE = 'trans dtrans dtrans-se hdb break-cj'
    US_AUDIO = "span.us source[type='audio/mpeg']"