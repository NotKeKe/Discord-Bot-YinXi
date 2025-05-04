import datetime

# def ext_events(sb_events, sb_cur_year, curtime):
#     def time_to_sb_date(time):
#         # Implement your timeToSBDate function here
#         pass

string = "1736709300000"
string = int(string) / 1000

a = [   (   "Jacob's Farming Contest",
        {   'start': datetime.datetime(2025, 1, 8, 0, 15),
            'end': datetime.datetime(2025, 1, 8, 0, 35),
            'startTime': 1736266500000,
            'endTime': 1736267700000,
            'TimeLeft': -343742,
            'SBDate': '30/3/395'}),
        (   'Special Mayor Election',
        {   'start': datetime.datetime(2025, 1, 24, 18, 15),
            'end': datetime.datetime(2025, 1, 28, 15, 15),
            'startTime': 1737713700000,
            'endTime': 1738048500000,
            'TimeLeft': 1446856258,
            'SBDate': '27/6/398'})
    ]

print(a[1][1]['startTime'])

# print(int(string))

# a1 = tuple()

# a1 = ('a', 'b')

# lst = list([a1, 'c'])

a = [('awdjwaid', {'a': 'b'}), ()]
print(a[0][1]['a'])

# Skyblock 中一天的秒數
SECONDS_PER_SKYBLOCK_DAY = 1200  # 20 分鐘
# Skyblock 中一年有 124 天
DAYS_PER_SKYBLOCK_YEAR = 124

# 當前時間
now = datetime.datetime.now()

# 計算當前 Skyblock 年份和天數
skyblock_start_date = datetime.datetime(2019, 6, 11)
days_since_skyblock_start = (now - skyblock_start_date).days
skyblock_year = days_since_skyblock_start // DAYS_PER_SKYBLOCK_YEAR + 1
skyblock_day_of_year = days_since_skyblock_start % DAYS_PER_SKYBLOCK_YEAR + 1

print(skyblock_year)
