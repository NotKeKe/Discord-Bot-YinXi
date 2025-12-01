import asyncio
import itertools
import os
import inspect
from typing import Any

class MyPriorityQueue:
    def __init__(self):
        self._queue = asyncio.PriorityQueue()
        self._task_registry = {} # 記錄最新的優先級 {task_id: priority}
        self._running_tasks = set() # 記錄目前正在跑的 task_id (防止同 ID 雙重執行)
        self.results = {}
        self._counter = itertools.count()

        self.workers = [asyncio.create_task(worker(i, self)) for i in range(os.cpu_count())]

    async def add_task(self, task_id: str, priority: int, function):
        self._task_registry[task_id] = priority
        await self._queue.put((priority, next(self._counter), task_id, function))
        # print(f"📥 [加入/變更] {task_id} (Prio: {priority})")

    async def get_task(self):
        while True:
            priority, count, task_id, function = await self._queue.get()

            # check 
            latest_priority = self._task_registry.get(task_id)
            
            if latest_priority is None or priority != latest_priority:
                self._queue.task_done()
                continue

            # 3. 【關鍵修改】檢查是否「正在執行中」
            # 如果這個 ID 已經有別的 Worker 在跑，我們不能同時跑
            # 我們把它「塞回」佇列，稍後再處理
            if task_id in self._running_tasks:
                # 簡單策略：放回去讓別人處理，或者自己稍微等一下再試
                # 這裡選擇放回 Queue (重新排隊)
                self._queue.task_done()
                # 稍微 delay 避免無窮迴圈造成的 CPU 飆高
                await asyncio.sleep(0.1) 
                await self._queue.put((priority, count, task_id, function))
                continue

            # 4. 鎖定這個 ID
            self._running_tasks.add(task_id)
            return task_id, function

    def finish_task(self, task_id: str, result: Any = None):
        # 解鎖 ID
        if task_id in self._running_tasks:
            self._running_tasks.remove(task_id)
            
        # 這裡可以決定是否要從 registry 刪除
        # 如果這是「一次性任務」，就刪除 registry
        if task_id in self._task_registry:
            del self._task_registry[task_id]

        if result is not None:
            self.results[task_id] = result
            
        self._queue.task_done()

    async def get_result(self, task_id: str) -> Any:
        '''
        It's a method to get the result of a task
        '''
        while task_id not in self.results:
            await asyncio.sleep(0.1)

        result = self.results[task_id]
        del self.results[task_id]
        return result

# --- 測試多併發 ---

async def worker(worker_id: int, queue: MyPriorityQueue):
    # print(f"🤖 Worker-{worker_id} 啟動")
    try:
        while True:
            task_id, function = await queue.get_task()
            
            # print(f"🚀 [Worker-{worker_id}] 執行: {task_id}")
            # 模擬不同長度的工作時間
            # function should be awaitable
            if inspect.isawaitable(function):
                result = await function
            else:
                raise NotImplementedError
            # await asyncio.sleep(random.randint(1, 5))
            # print(f"✅ [Worker-{worker_id}] 完成: {task_id}")
            
            queue.finish_task(task_id, result)
    except asyncio.CancelledError:
        # print(f"💀 Worker-{worker_id} 下班")
        ...

async def _main():
    dpq = MyPriorityQueue()
    
    # --- 重點：這裡決定了併發數量 (Limit) ---
    # 我們啟動 3 個 Worker，表示同時最多有 3 個任務在跑
    workers = [asyncio.create_task(worker(i, dpq)) for i in range(3)]

    print("--- 系統啟動 (3 Workers) ---\n")

    # 1. 瞬間丟入 5 個任務
    await dpq.add_task("A", 10, lambda x: "任務 A (Prio 10)")
    await dpq.add_task("B", 10, lambda x: "任務 B (Prio 10)")
    await dpq.add_task("C", 10, lambda x: "任務 C (Prio 10)")
    await dpq.add_task("D", 10, lambda x: "任務 D (Prio 10)")
    await dpq.add_task("E", 10, lambda x: "任務 E (Prio 10)")

    # 此時 Worker 1, 2, 3 會分別抓走 A, B, C (同時執行)
    # D, E 還在排隊
    
    await asyncio.sleep(0.1) 
    print("\n--- 插隊測試 ---\n")
    
    # 2. 突然插入超級急件
    await dpq.add_task("F", 1, lambda x: "🔥 任務 F (急件 Prio 1)")

    # 預期行為：
    # 當 A, B, C 之中任何一個 Worker 完成後，
    # 下一個被抓出來的一定是 F (因為它是 Prio 1)，而不是 D 或 E

    await dpq._queue.join()
    
    for w in workers: w.cancel()
    await asyncio.gather(*workers, return_exceptions=True)