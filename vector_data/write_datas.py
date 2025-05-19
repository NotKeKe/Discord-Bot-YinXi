from cmds.AIsTwo.tools.tool_funcs import wiki_searh
def write(query: str, path: str = './vector_data/test.txt'):
    '''This is a function to save wiki data to a test.txt'''
    f = open(path, mode='w', encoding='utf8')
    f.write(wiki_searh(query))
    f.close()