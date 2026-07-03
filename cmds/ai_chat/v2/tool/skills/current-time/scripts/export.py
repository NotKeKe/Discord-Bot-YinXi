from datetime import datetime, timezone, timedelta

class Tool:
    def call(self, time_offset: int = 8) -> str:
        time = datetime.now(timezone(timedelta(hours=time_offset)))
        return time.strftime("%Y-%m-%d %H:%M:%S %z")