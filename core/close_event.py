import asyncio
import logging

logger = logging.getLogger(__name__)

async def close_event():
    from core.functions import mongo_db_client, redis_client
    from core.playwright import (
        p, browser, contexts, 
        close_context_task, close_browser_task
    )

    from core.classes import get_bot
    bot = get_bot()


    if mongo_db_client:
        try: mongo_db_client.close(); logger.info('Closed mongodb client')
        except: logger.error('Cannot close mongo client', exc_info=True)

    if redis_client:
        try: await redis_client.close(True); logger.info('Closed redis client')
        except: logger.error('Cannot close redis client', exc_info=True)

    try:
        for context in contexts:
            await context.close()
        contexts = {}
        if browser:
            await browser.close()
        if p:
            await p.stop()

        tasks = []
        if close_context_task:
            close_context_task.cancel()
            tasks.append(close_context_task)
            close_context_task = None
        if close_browser_task:
            close_browser_task.cancel()
            tasks.append(close_browser_task)
            close_browser_task = None
        if tasks:
            try: await asyncio.gather(*tasks)
            except asyncio.CancelledError: ...
        logger.info('Closed global playwright')
    except:
        logger.error('Cannot close global playwright', exc_info=True)

    try: await bot.close()
    except: logger.error('Cannot close bot', exc_info=True)