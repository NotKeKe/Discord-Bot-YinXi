import sqlite3

def knowledge_base():
    connection = sqlite3.connect('./cmds/AIsTwo/data/knowledge_base.db')
    cursor = connection.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY,
            question TEXT,
            answer TEXT,
            tags TEXT,
            source TEXT
        )
    ''')
    connection.commit()
    return connection, cursor

def user_preferences():
    connection = sqlite3.connect("./cmds/AIsTwo/data/userPrefs.db")
    cursor = connection.cursor()
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS preferences (
                    id INTEGER PRIMARY KEY, 
                    user_id INTEGER,
                    preference TEXT
                   ) 
                   ''')
    connection.commit()
    return connection, cursor

