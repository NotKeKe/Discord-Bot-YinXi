import time
from datetime import datetime
import json
import pprint
from pprint import PrettyPrinter

MC_DAY = 1200000
MC_MONTH = 37200000
MC_YEAR = 446400000  # Real Life ms
MC_HOUR = MC_DAY / 24
MC_MINUTE = MC_HOUR / 60
SB_NEWYEAR = 1560275700000  # Skyblock Year 1
IRL_HOUR = 3600000
SB_SEASON_NAMES = [
    'Early Spring',
    'Spring',
    'Late Spring',
    
    'Early Summer',
    'Summer',
    'Late Summer',
    
    'Early Autumn',
    'Autumn',
    'Late Autumn',
    
    'Early Winter',
    'Winter',
    'Late Winter'
]

def format_time(x):
    x = x // 1000
    d = x // 86400
    h = (x % 86400) // 3600
    m = (x % 3600) // 60
    s = x % 60

    ret = ''
    if x >= 3600:
        if x >= 86400:
            ret += f'{d}d '
        ret += f'{h}h '
    ret += f'{m}m {s}s'
    return ret

def sb_get_season(n):
    return SB_SEASON_NAMES[n - 1]

CUSTOM_OFFSET = 0

class LocalStorage:
    FISHING_FESTIVAL = 'false'

def get_fishing_festival():
    return LocalStorage.FISHING_FESTIVAL == 'true'

def set_fishing_festival(x):
    LocalStorage.FISHING_FESTIVAL = str(bool(x)).lower()

def sb_get_year(time):
    sb_curtime = (time - SB_NEWYEAR) % MC_YEAR
    sb_cur_year = time - sb_curtime
    return 1 + (sb_cur_year - SB_NEWYEAR) // MC_YEAR

def sb_day_of_the_year(time):
    sb_curtime = (time - SB_NEWYEAR) % MC_YEAR
    return (sb_curtime // MC_DAY) + 1

def time_to_sb_date(time, hours=False, obj=False):
    year = sb_get_year(time)
    time -= SB_NEWYEAR
    month = (time // MC_MONTH) % 12 + 1
    day = (time // MC_DAY) % 31 + 1
    hour = (time // MC_HOUR) % 24
    min = (time // MC_MINUTE) % 60
    hour = str(hour).zfill(2)
    min = str(min).zfill(2)
    
    if obj:
        return {
            'day': day,
            'month': month,
            'year': year,
            'hour': hour,
            'min': min
        }
    daytime = f' {hour}:{min}' if hours else ''
    return f'{day}/{month}/{year}{daytime}'

def sb_date(d=1, m=1):
    d -= 1
    m -= 1
    return d * MC_DAY + m * MC_MONTH

def date2sb_date(curtime, raw):
    curtime -= SB_NEWYEAR
    if raw:
        return curtime
    return [curtime // MC_DAY % 31 + 1, curtime // MC_MONTH % 12 + 1, curtime // MC_YEAR + 1]

def sb_get_next_events():
    curtime = int(time.time() * 1000) + CUSTOM_OFFSET

    sb_curtime = (curtime - SB_NEWYEAR) % MC_YEAR
    sb_cur_year = curtime - sb_curtime

    def fishing_festival(offset=1):
        if (sb_curtime % MC_MONTH) < IRL_HOUR:
            offset -= 1
        start = sb_curtime - (sb_curtime % MC_MONTH) + MC_MONTH * offset
        end = start + IRL_HOUR
        return [start, end]

    def special_mayor_elections():
        SB_YEAR = sb_get_year(curtime)
        SpecialYear = (SB_YEAR % 8) if (SB_YEAR % 8) != 0 else 0
        SpecialDiff = SB_YEAR - (SB_YEAR // 8) * 8
        if SpecialDiff == 1 and sb_curtime < sb_date(27, 3):
            return sb_event(27 - 372, 6, 279)
        return sb_event(27 + 372 * SpecialYear, 6, 279)

    def sb_event(day, month, duration):
        start = sb_date(day, month)
        end = start + MC_DAY * duration
        if end < sb_curtime:
            start += MC_YEAR
            end += MC_YEAR
        return [start, end]

    def dark_auction():
        start = sb_curtime - (sb_curtime % IRL_HOUR) + IRL_HOUR
        end = start + 34166
        return [start, end]

    def jacob_event():
        hmins = sb_curtime % IRL_HOUR
        
        if hmins < MC_DAY * 2:
            hmins += IRL_HOUR
        start = sb_curtime - hmins + IRL_HOUR + MC_DAY
        end = start + MC_DAY
        return [start, end]

    sb_events = [
        ["Election Over", sb_event(27, 3, 0)],
        ["Traveling Zoo", sb_event(1, 4, 3)],
        ["Election Start", sb_event(27, 6, 0)],
        ["Spooky Festival", sb_event(29, 8, 3)],
        ["Traveling Zoo", sb_event(1, 10, 3)],
        ["Jerry's Workshop", sb_event(1, 12, 31)],
        ["Season Of Jerry", sb_event(24, 12, 3)],
        ["New Year Cake", sb_event(29, 12, 3)],
        ["Dark Auction", dark_auction()],
        ["Jacob's Farming Contest", jacob_event()],
        ["Special Mayor Election", special_mayor_elections()]
    ]

    if LocalStorage.FISHING_FESTIVAL == 'true':
        sb_events.extend([
            ["Fishing Festival", fishing_festival()],
            ["Fishing Festival", fishing_festival(2)],
            ["Fishing Festival", fishing_festival(3)],
            ["Fishing Festival", fishing_festival(4)],
            ["Fishing Festival", fishing_festival(5)],
            ["Fishing Festival", fishing_festival(6)]
        ])
        

    sorted_events = sorted(sb_events, key=lambda x: x[1][0])
    mapped_events = []

    for x in sorted_events:
        start_timestamp = (sb_cur_year + x[1][0]) / 1000 
        end_timestamp = (sb_cur_year + x[1][1]) / 1000
        event = {
            'start': datetime.fromtimestamp(start_timestamp),
            'end': datetime.fromtimestamp(end_timestamp),
            'startTime': sb_cur_year + x[1][0],
            'endTime': sb_cur_year + x[1][1],
            'TimeLeft': (sb_cur_year + x[1][0] - curtime),
            'SBDate': time_to_sb_date(sb_cur_year + x[1][0])
        }
        mapped_events.append((x[0], event))

    return mapped_events

# 顯示下一個事件
def show_next_events(update=False) -> dict:
    curtime = int(time.time() * 1000)  # 當前時間的毫秒數
    sb_year = sb_get_year(curtime)
    # print(f'CURRENT SKYBLOCK YEAR: {sb_year}')

    events = sb_get_next_events()

    pp = PrettyPrinter(indent=4, width=80, depth=3, sort_dicts=False)

    pp.pprint(events)

    output = {'data_update_time': datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
              'sb_year': str(sb_year)}
    i = 0

    for event in events:
        event_name = event[0]
        event_start = datetime.fromtimestamp((curtime + event[1]['startTime']) / 1000).strftime("%Y/%m/%d %H:%M:%S")
        event_end = datetime.fromtimestamp((curtime + event[1]['endTime']) / 1000).strftime("%Y/%m/%d %H:%M:%S")
        time_left = format_time(event[1]['TimeLeft'] - curtime)
        sb_date = time_to_sb_date(curtime + event[1]['startTime'])

        output[str(event_name)] = {
            'Start': str(event_start),
            'End': str(event_end),
            'Time Left': str(time_left),
            'Skyblock Date': str(sb_date)
        }

        with open('./cmds/skyblock_commands_foldor/tmp.txt', mode='w') as f:
            json.dump(output, f, indent=4)
        i += 1

    return output

        # print(f'Event: {event_name}')
        # print(f'Start: {event_start}')
        # print(f'End: {event_end}')
        # print(f'Time Left: {time_left}')
        # print(f'Skyblock Date: {sb_date}')
        # print('---')

# 更新剩餘時間
def update_time_left():
    curtime = int(time.time() * 1000)  # 當前時間的毫秒數
    events = sb_get_next_events()
    for event in events:
        time_left = format_time(event[1][0] - curtime)
        print(f'Event: {event[0]}, Time Left: {time_left}')

# 測試顯示下一個事件


if __name__  == "__main__":
    show_next_events()
    # curtime = int(time.time() * 1000)  # 當前時間的毫秒數
    # sb_year = sb_get_year(curtime)
    # # print(f'CURRENT SKYBLOCK YEAR: {sb_year}')

    # events = sb_get_next_events()

    # pp = PrettyPrinter(indent=4, width=80, depth=3, sort_dicts=False)

    # # pp.pprint(events)

    # output = {'data_update_time': datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
    #           'sb_year': str(sb_year)}
    # i = 0

    # for event in events:
    #     event_name = event[0]
    #     print(event[])
    #     i += 1
