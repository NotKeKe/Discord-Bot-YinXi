import aiosqlite

class AioSqlite:
    def __init__(self, db_path):
        self.db_path = db_path

    async def execute(self, query: str, params: tuple = ()):
        """执行 SQL 语句（增删改）"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(query, params)
            await db.commit()

    async def fetch_one(self, query: str, params: tuple = ()):
        """获取单个数据"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(query, params) as cursor:
                return await cursor.fetchone()

    async def fetch_all(self, query: str, params: tuple = ()):
        """获取所有数据"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(query, params) as cursor:
                return await cursor.fetchall()

    async def create_table(self, query: str):
        """创建数据表
        Example:
        ```
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            age INTEGER
        )
        ```
        """
        await self.execute(query)

    async def run(self, query: str, params: tuple = ()):
        await self.execute(query, params)
    
    async def init(self, query: str):
        await self.create_table(query)

    async def exists(self, query: str, params: tuple = ()) -> bool:
        '''
        Example:
        ```
        await db.exists("SELECT 1 FROM users WHERE name = ?", ("Alice",))
        ```
        '''
        result = await self.fetch_one(f"SELECT EXISTS({query})", params)
        return bool(result[0])
