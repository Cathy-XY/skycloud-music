import sqlite3
import os
from config import DATABASE_PATH, DB_TYPE, MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB

# ---- SQL 兼容层 ----
# 让 models.py 的 SQL 同时兼容 SQLite 和 MySQL

def sql(query):
    """将 SQLite 风格的 ? 占位符转为 MySQL 的 %s"""
    if DB_TYPE == 'mysql':
        return query.replace('?', '%s')
    return query


def now_expr():
    """返回当前时间的 SQL 表达式"""
    if DB_TYPE == 'mysql':
        return "NOW()"
    return "datetime('now', '+8 hours')"


def last_id_expr():
    """返回最后插入行 ID 的 SQL 表达式"""
    if DB_TYPE == 'mysql':
        return "LAST_INSERT_ID()"
    return "last_insert_rowid()"


# ---- 连接管理 ----

def get_db():
    if DB_TYPE == 'mysql':
        return _get_mysql()
    return _get_sqlite()


def _get_sqlite():
    conn = sqlite3.connect(DATABASE_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _get_mysql():
    import pymysql
    import pymysql.converters
    conv = pymysql.converters.conversions.copy()
    conv[7] = str   # TIMESTAMP → 字符串
    conv[12] = str  # DATETIME → 字符串
    conn = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
        conv=conv,
    )
    return conn


# ---- MySQL 连接的包装器 ----
# pymysql 的 connection 没有 execute/executescript/fetchone 等直接方法
# 为了让 models.py 代码改动最小，提供一个轻量包装器

class MySQLConnectionWrapper:
    """让 pymysql connection 的接口与 sqlite3.Connection 接近"""
    def __init__(self, conn):
        self._conn = conn
        self._cursor = conn.cursor()

    def execute(self, query, params=None):
        self._cursor.execute(query, params or ())
        return self._cursor

    def commit(self):
        self._conn.commit()

    def close(self):
        self._cursor.close()
        self._conn.close()

    @property
    def lastrowid(self):
        return self._cursor.lastrowid


def get_conn():
    """返回统一接口的数据库连接。models.py 应使用此函数。"""
    if DB_TYPE == 'mysql':
        raw = _get_mysql()
        return MySQLConnectionWrapper(raw)
    return _get_sqlite()


# ---- 初始化 ----

_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT    NOT NULL UNIQUE,
    password    TEXT    NOT NULL,
    nickname    TEXT    NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', '+8 hours'))
);

CREATE TABLE IF NOT EXISTS songs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    artist      TEXT    NOT NULL DEFAULT 'Unknown',
    filename    TEXT    NOT NULL UNIQUE,
    duration    REAL    DEFAULT 0,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', '+8 hours'))
);

CREATE TABLE IF NOT EXISTS comments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    song_id     INTEGER NOT NULL REFERENCES songs(id),
    user_id     INTEGER NOT NULL REFERENCES users(id),
    content     TEXT    NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', '+8 hours'))
);

CREATE TABLE IF NOT EXISTS lyrics (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    song_id     INTEGER NOT NULL UNIQUE REFERENCES songs(id),
    content     TEXT    NOT NULL DEFAULT '',
    edited_by   INTEGER REFERENCES users(id),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', '+8 hours'))
);

CREATE TABLE IF NOT EXISTS lyrics_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    song_id     INTEGER NOT NULL REFERENCES songs(id),
    user_id     INTEGER NOT NULL REFERENCES users(id),
    content     TEXT    NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', '+8 hours'))
);

CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    content     TEXT    NOT NULL,
    reply_to    INTEGER REFERENCES messages(id),
    image_url   TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', '+8 hours'))
);

CREATE INDEX IF NOT EXISTS idx_comments_song_id ON comments(song_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
CREATE INDEX IF NOT EXISTS idx_lyrics_song_id ON lyrics(song_id);

CREATE TABLE IF NOT EXISTS line_comments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    song_id     INTEGER NOT NULL REFERENCES songs(id),
    line_index  INTEGER NOT NULL,
    line_text   TEXT    NOT NULL,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    content     TEXT    NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', '+8 hours'))
);

CREATE INDEX IF NOT EXISTS idx_line_comments_song ON line_comments(song_id, line_index);
"""

_MYSQL_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id          INT PRIMARY KEY AUTO_INCREMENT,
        username    VARCHAR(100) NOT NULL UNIQUE,
        password    VARCHAR(255) NOT NULL,
        nickname    VARCHAR(100) NOT NULL,
        created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS songs (
        id          INT PRIMARY KEY AUTO_INCREMENT,
        title       VARCHAR(500) NOT NULL,
        artist      VARCHAR(200) NOT NULL DEFAULT 'Unknown',
        filename    VARCHAR(500) NOT NULL UNIQUE,
        duration    DOUBLE DEFAULT 0,
        created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS comments (
        id          INT PRIMARY KEY AUTO_INCREMENT,
        song_id     INT NOT NULL,
        user_id     INT NOT NULL,
        content     TEXT NOT NULL,
        created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (song_id) REFERENCES songs(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS lyrics (
        id          INT PRIMARY KEY AUTO_INCREMENT,
        song_id     INT NOT NULL UNIQUE,
        content     TEXT NOT NULL,
        edited_by   INT,
        updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (song_id) REFERENCES songs(id),
        FOREIGN KEY (edited_by) REFERENCES users(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS lyrics_history (
        id          INT PRIMARY KEY AUTO_INCREMENT,
        song_id     INT NOT NULL,
        user_id     INT NOT NULL,
        content     TEXT NOT NULL,
        created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (song_id) REFERENCES songs(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS messages (
        id          INT PRIMARY KEY AUTO_INCREMENT,
        user_id     INT NOT NULL,
        content     TEXT NOT NULL,
        reply_to    INT,
        image_url   VARCHAR(500),
        created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (reply_to) REFERENCES messages(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS line_comments (
        id          INT PRIMARY KEY AUTO_INCREMENT,
        song_id     INT NOT NULL,
        line_index  INT NOT NULL,
        line_text   TEXT NOT NULL,
        user_id     INT NOT NULL,
        content     TEXT NOT NULL,
        created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (song_id) REFERENCES songs(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
]

_MYSQL_INDEXES = [
    "CREATE INDEX idx_comments_song_id ON comments(song_id)",
    "CREATE INDEX idx_messages_created_at ON messages(created_at)",
    "CREATE INDEX idx_lyrics_song_id ON lyrics(song_id)",
    "CREATE INDEX idx_line_comments_song ON line_comments(song_id, line_index)",
]


def init_db():
    if DB_TYPE == 'mysql':
        _init_mysql()
    else:
        _init_sqlite()


def _init_sqlite():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = _get_sqlite()
    conn.executescript(_SQLITE_SCHEMA)
    conn.commit()
    _migrate_sqlite(conn)
    conn.close()


def _migrate_sqlite(conn):
    """增量迁移，兼容已有 SQLite 数据库"""
    columns = [row[1] for row in conn.execute("PRAGMA table_info(messages)").fetchall()]
    if 'reply_to' not in columns:
        conn.execute("ALTER TABLE messages ADD COLUMN reply_to INTEGER REFERENCES messages(id)")
        conn.commit()
    if 'image_url' not in columns:
        conn.execute("ALTER TABLE messages ADD COLUMN image_url TEXT")
        conn.commit()


def _init_mysql():
    import pymysql
    conn = _get_mysql()
    cursor = conn.cursor()
    for ddl in _MYSQL_TABLES:
        cursor.execute(ddl)
    for idx_sql in _MYSQL_INDEXES:
        try:
            cursor.execute(idx_sql)
        except pymysql.err.OperationalError as e:
            if e.args[0] == 1061:  # Duplicate key name — index already exists
                pass
            else:
                raise
    conn.commit()
    cursor.close()
    conn.close()
    print(f"[MySQL] Connected to {MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}")
