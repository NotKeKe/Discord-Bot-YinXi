import time
from cpython.unicode cimport PyUnicode_Join


def ac_string(object SkyblockItemTracker, object sb, dict obj, list ac_data, long channelID):
    """
    obj: data[ctx.guild.id] (dict)
    ac_data: auctions['auctions'] (list of dicts)
    """
    cdef list string_list = []
    cdef dict ac_item
    cdef str item, username, price
    cdef deleted

    for item in obj['items']:
        string_list.append(f'### {item}')
        for ac_item in ac_data:
            if (
                ac_item['item_name'].endswith(item) and 
                ac_item['bin'] and 
                not ac_item['claimed']
                and ac_item['item_uuid'] not in SkyblockItemTracker.tracked_item[channelID]
            ):
                username = sb.get_username_from_uuid(ac_item['auctioneer'])
                price = sb.format_price(ac_item['starting_bid'])
                string_list.append(f"From {username}: {price}")

                SkyblockItemTracker.tracked_item[channelID].append(ac_item['item_uuid'])

        if string_list[-1] == f'### {item}':
            deleted = string_list.pop()
    
    # 使用 Cython 內建的 `PyUnicode_Join` 來提高字串拼接效率
    return PyUnicode_Join("\n", string_list)


