import asyncio

TASKS: set[asyncio.Task] = set()

def add_task(task: asyncio.Task):
    TASKS.add(task)

async def close_all_tasks():
    for task in TASKS:
        task.cancel()

    await asyncio.gather(*TASKS, return_exceptions=True)

async def del_task_event():
    '''定期清理完成的 task'''
    while True:
        for task in TASKS.copy():
            if task.done():
                TASKS.discard(task)
        await asyncio.sleep(10)