import logging
import logging.handlers
from pathlib import Path
import sys

log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

def setup_logging():
    # 1. 定義格式
    log_format = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 2. 設定 Handler (包含你的 TimedRotatingFileHandler)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)

    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=log_dir / "bot.log",
        when='D',
        interval=1,
        backupCount=10,
        encoding="utf-8",
    )
    file_handler.setFormatter(log_format)

    # 3. 設定 Root Logger (捕捉所有未被攔截的 log)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # 清除舊有的 handlers 避免重複
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # 4. --- 新增：接管 Uvicorn 的 Logger ---
    # Uvicorn 有這三個主要的 logger，我們要強制它們使用我們的設定
    uvicorn_loggers = ["uvicorn", "uvicorn.access", "uvicorn.error"]
    
    for logger_name in uvicorn_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        
        # 關鍵：將 handlers 清空，並設為 propagate=True
        # 這樣 Uvicorn 的 log 就會自動「冒泡」傳遞給 root_logger
        # 由 root_logger 統一寫入檔案和終端機
        logger.handlers = [] 
        logger.propagate = True 

    # 5. 調整第三方庫的 log 等級 (維持你原本的設定)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

class StreamToLogger:
    def __init__(self, logger, level):
        self.logger = logger
        self.level = level

    def write(self, message):
        if message.rstrip() != "":
            self.logger.log(self.level, message.rstrip())

    def flush(self):
        pass

    def isatty(self):
        return False

# 執行設定
setup_logging()

# 重導向 stdout/stderr
sys.stdout = StreamToLogger(logging.getLogger("stdout"), logging.INFO)
sys.stderr = StreamToLogger(logging.getLogger("stderr"), logging.ERROR)