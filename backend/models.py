import re
import os
import tempfile
from database import get_conn, sql, now_expr, last_id_expr
from config import MUSIC_DIR, STORAGE_TYPE


def parse_filename(filename):
    name = filename.rsplit('.', 1)[0]
    name = re.sub(r'^\d+\.', '', name)
    for sep in ['+-+', ' - ', '-']:
        if sep in name:
            parts = name.split(sep, 1)
            artist = parts[0].strip()
            title = parts[1].strip()
            if artist and title:
                return title, artist
    return name.strip(), 'Unknown'


def scan_songs():
    if STORAGE_TYPE in ('oss', 'bos'):
        _scan_songs_cloud()
    else:
        _scan_songs_local()


def _scan_songs_local():
    if not os.path.isdir(MUSIC_DIR):
        return
    conn = get_conn()
    local_files = [f for f in os.listdir(MUSIC_DIR) if f.lower().endswith('.mp3')]
    # 构建 lrc 文件映射：base_name(小写) -> lrc 文件名
    local_lrc_files = [f for f in os.listdir(MUSIC_DIR) if f.lower().endswith('.lrc')]
    lrc_map = {}
    for lrc_fname in local_lrc_files:
        base = lrc_fname.rsplit('.', 1)[0]
        lrc_map[base.lower()] = lrc_fname

    _NOW = now_expr()

    for fname in local_files:
        existing = conn.execute(sql("SELECT id FROM songs WHERE filename = ?"), (fname,)).fetchone()
        if existing:
            song_id = existing['id']
        else:
            title, artist = parse_filename(fname)
            duration = 0
            try:
                from mutagen.mp3 import MP3
                audio = MP3(os.path.join(MUSIC_DIR, fname))
                duration = audio.info.length
            except Exception:
                pass
            conn.execute(
                sql("INSERT INTO songs (title, artist, filename, duration) VALUES (?, ?, ?, ?)"),
                (title, artist, fname, duration)
            )
            row = conn.execute(sql("SELECT id FROM songs WHERE filename = ?"), (fname,)).fetchone()
            song_id = row['id']
        has_lyrics = conn.execute(sql("SELECT id FROM lyrics WHERE song_id = ?"), (song_id,)).fetchone()

        # 检查同名 .lrc 文件
        mp3_base = fname.rsplit('.', 1)[0]
        lrc_key = lrc_map.get(mp3_base.lower())

        if lrc_key:
            try:
                lrc_path = os.path.join(MUSIC_DIR, lrc_key)
                try:
                    with open(lrc_path, 'r', encoding='utf-8') as f:
                        lrc_content = f.read().strip()
                except UnicodeDecodeError:
                    with open(lrc_path, 'r', encoding='gbk') as f:
                        lrc_content = f.read().strip()
                if lrc_content:
                    if has_lyrics:
                        conn.execute(
                            sql(f"UPDATE lyrics SET content = ?, updated_at = {_NOW} WHERE song_id = ?"),
                            (lrc_content, song_id)
                        )
                    else:
                        conn.execute(
                            sql("INSERT INTO lyrics (song_id, content) VALUES (?, ?)"),
                            (song_id, lrc_content)
                        )
            except Exception:
                pass
        elif not has_lyrics:
            lrc = extract_lrc_from_mp3(os.path.join(MUSIC_DIR, fname))
            if lrc:
                conn.execute(
                    sql("INSERT INTO lyrics (song_id, content) VALUES (?, ?)"),
                    (song_id, lrc)
                )
    _sync_delete_missing(conn, local_files)
    conn.commit()
    conn.close()


def _scan_songs_cloud():
    from storage import list_cloud_songs, list_cloud_lrc_files, download_from_cloud
    filenames = list_cloud_songs()
    lrc_files = list_cloud_lrc_files()
    lrc_map = {}
    for lrc_fname in lrc_files:
        base = lrc_fname.rsplit('.', 1)[0]
        lrc_map[base.lower()] = lrc_fname

    _NOW = now_expr()
    conn = get_conn()
    for fname in filenames:
        existing = conn.execute(sql("SELECT id FROM songs WHERE filename = ?"), (fname,)).fetchone()
        if existing:
            song_id = existing['id']
        else:
            title, artist = parse_filename(fname)
            duration = 0
            tmp_path = os.path.join(tempfile.gettempdir(), 'cloud_scan', fname)
            try:
                download_from_cloud(fname, tmp_path)
                from mutagen.mp3 import MP3
                audio = MP3(tmp_path)
                duration = audio.info.length
            except Exception:
                pass
            conn.execute(
                sql("INSERT INTO songs (title, artist, filename, duration) VALUES (?, ?, ?, ?)"),
                (title, artist, fname, duration)
            )
            row = conn.execute(sql("SELECT id FROM songs WHERE filename = ?"), (fname,)).fetchone()
            song_id = row['id']
        has_lyrics = conn.execute(sql("SELECT id FROM lyrics WHERE song_id = ?"), (song_id,)).fetchone()

        mp3_base = fname.rsplit('.', 1)[0]
        lrc_key = lrc_map.get(mp3_base.lower())

        if lrc_key:
            lrc_content = _download_lrc_content(lrc_key)
            if lrc_content:
                if has_lyrics:
                    conn.execute(
                        sql(f"UPDATE lyrics SET content = ?, updated_at = {_NOW} WHERE song_id = ?"),
                        (lrc_content, song_id)
                    )
                else:
                    conn.execute(
                        sql("INSERT INTO lyrics (song_id, content) VALUES (?, ?)"),
                        (song_id, lrc_content)
                    )
        elif not has_lyrics:
            tmp_path = os.path.join(tempfile.gettempdir(), 'cloud_scan', fname)
            if not os.path.exists(tmp_path):
                try:
                    download_from_cloud(fname, tmp_path)
                except Exception:
                    continue
            lrc = extract_lrc_from_mp3(tmp_path)
            if lrc:
                conn.execute(
                    sql("INSERT INTO lyrics (song_id, content) VALUES (?, ?)"),
                    (song_id, lrc)
                )
    _sync_delete_missing(conn, filenames)
    conn.commit()
    conn.close()


def _download_lrc_content(lrc_filename):
    """从云存储下载 .lrc 文件并返回其文本内容"""
    from storage import download_from_cloud
    tmp_path = os.path.join(tempfile.gettempdir(), 'cloud_scan', lrc_filename)
    try:
        download_from_cloud(lrc_filename, tmp_path)
        try:
            with open(tmp_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
        except UnicodeDecodeError:
            with open(tmp_path, 'r', encoding='gbk') as f:
                content = f.read().strip()
        return content if content else None
    except Exception:
        return None


def extract_lrc_from_mp3(filepath):
    try:
        from mutagen.id3 import ID3
        tags = ID3(filepath)
        for key in tags:
            if key.startswith('USLT'):
                text = str(tags[key])
                if '[' in text and ']' in text:
                    return text
        if 'TEXT' in tags:
            text = str(tags['TEXT'])
            if '[' in text and ']' in text:
                return text
    except Exception:
        pass
    return None


def _sync_delete_missing(conn, existing_filenames):
    """删除 DB 中存在但文件列表中已不存在的歌曲及其关联数据"""
    db_songs = conn.execute("SELECT id, filename FROM songs").fetchall()
    cloud_set = set(existing_filenames)
    for song in db_songs:
        if song['filename'] not in cloud_set:
            sid = song['id']
            conn.execute(sql("DELETE FROM line_comments WHERE song_id = ?"), (sid,))
            conn.execute(sql("DELETE FROM comments WHERE song_id = ?"), (sid,))
            conn.execute(sql("DELETE FROM lyrics_history WHERE song_id = ?"), (sid,))
            conn.execute(sql("DELETE FROM lyrics WHERE song_id = ?"), (sid,))
            conn.execute(sql("DELETE FROM songs WHERE id = ?"), (sid,))


# --- User queries ---

def create_user(username, password_hash, nickname):
    conn = get_conn()
    try:
        conn.execute(
            sql("INSERT INTO users (username, password, nickname) VALUES (?, ?, ?)"),
            (username, password_hash, nickname)
        )
        conn.commit()
        user = conn.execute(sql("SELECT id, username, nickname FROM users WHERE username = ?"), (username,)).fetchone()
        return dict(user)
    finally:
        conn.close()


def get_user_by_username(username):
    conn = get_conn()
    user = conn.execute(sql("SELECT * FROM users WHERE username = ?"), (username,)).fetchone()
    conn.close()
    return dict(user) if user else None


def get_user_by_id(user_id):
    conn = get_conn()
    user = conn.execute(sql("SELECT id, username, nickname, created_at FROM users WHERE id = ?"), (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None


# --- Song queries ---

def get_all_songs():
    conn = get_conn()
    songs = conn.execute("SELECT id, title, artist, filename, duration, created_at FROM songs ORDER BY id").fetchall()
    conn.close()
    return [dict(s) for s in songs]


def get_song_by_id(song_id):
    conn = get_conn()
    song = conn.execute(sql("SELECT * FROM songs WHERE id = ?"), (song_id,)).fetchone()
    conn.close()
    return dict(song) if song else None


# --- Comment queries ---

def get_comments_by_song(song_id, page=1, per_page=20):
    conn = get_conn()
    offset = (page - 1) * per_page
    comments = conn.execute(sql("""
        SELECT c.id, c.content, c.created_at, u.nickname, u.id as user_id
        FROM comments c JOIN users u ON c.user_id = u.id
        WHERE c.song_id = ?
        ORDER BY c.created_at DESC
        LIMIT ? OFFSET ?
    """), (song_id, per_page, offset)).fetchall()
    conn.close()
    return [dict(c) for c in comments]


def create_comment(song_id, user_id, content):
    _NOW = now_expr()
    _LAST_ID = last_id_expr()
    conn = get_conn()
    conn.execute(
        sql(f"INSERT INTO comments (song_id, user_id, content, created_at) VALUES (?, ?, ?, {_NOW})"),
        (song_id, user_id, content)
    )
    conn.commit()
    comment = conn.execute(sql(f"""
        SELECT c.id, c.content, c.created_at, u.nickname, u.id as user_id
        FROM comments c JOIN users u ON c.user_id = u.id
        WHERE c.id = {_LAST_ID}
    """)).fetchone()
    conn.close()
    return dict(comment) if comment else None


def delete_comment(comment_id, user_id):
    conn = get_conn()
    result = conn.execute(sql("DELETE FROM comments WHERE id = ? AND user_id = ?"), (comment_id, user_id))
    conn.commit()
    deleted = result.rowcount > 0
    conn.close()
    return deleted


# --- Lyrics queries ---

def get_lyrics(song_id):
    conn = get_conn()
    row = conn.execute(sql("""
        SELECT l.content, l.updated_at, u.nickname as edited_by_name
        FROM lyrics l LEFT JOIN users u ON l.edited_by = u.id
        WHERE l.song_id = ?
    """), (song_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def save_lyrics(song_id, user_id, content):
    _NOW = now_expr()
    conn = get_conn()
    existing = conn.execute(sql("SELECT id FROM lyrics WHERE song_id = ?"), (song_id,)).fetchone()
    if existing:
        conn.execute(
            sql(f"UPDATE lyrics SET content = ?, edited_by = ?, updated_at = {_NOW} WHERE song_id = ?"),
            (content, user_id, song_id)
        )
    else:
        conn.execute(
            sql(f"INSERT INTO lyrics (song_id, content, edited_by, updated_at) VALUES (?, ?, ?, {_NOW})"),
            (song_id, content, user_id)
        )
    conn.execute(
        sql(f"INSERT INTO lyrics_history (song_id, user_id, content, created_at) VALUES (?, ?, ?, {_NOW})"),
        (song_id, user_id, content)
    )
    conn.commit()
    conn.close()


def get_lyrics_history(song_id):
    conn = get_conn()
    rows = conn.execute(sql("""
        SELECT lh.content, lh.created_at, u.nickname
        FROM lyrics_history lh JOIN users u ON lh.user_id = u.id
        WHERE lh.song_id = ?
        ORDER BY lh.created_at DESC
        LIMIT 20
    """), (song_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- Message queries ---

def get_messages(page=1, per_page=50):
    conn = get_conn()
    offset = (page - 1) * per_page
    msgs = conn.execute(sql("""
        SELECT m.id, m.content, m.reply_to, m.image_url, m.created_at,
               u.nickname, u.id as user_id,
               rm.content as reply_content,
               rm.image_url as reply_image_url,
               ru.nickname as reply_nickname
        FROM messages m
        JOIN users u ON m.user_id = u.id
        LEFT JOIN messages rm ON m.reply_to = rm.id
        LEFT JOIN users ru ON rm.user_id = ru.id
        ORDER BY m.created_at DESC
        LIMIT ? OFFSET ?
    """), (per_page, offset)).fetchall()
    conn.close()
    return [dict(m) for m in msgs]


def create_message(user_id, content, reply_to=None, image_url=None):
    _NOW = now_expr()
    _LAST_ID = last_id_expr()
    conn = get_conn()
    conn.execute(
        sql(f"INSERT INTO messages (user_id, content, reply_to, image_url, created_at) VALUES (?, ?, ?, ?, {_NOW})"),
        (user_id, content, reply_to, image_url)
    )
    conn.commit()
    msg = conn.execute(sql(f"""
        SELECT m.id, m.content, m.reply_to, m.image_url, m.created_at, u.nickname, u.id as user_id
        FROM messages m JOIN users u ON m.user_id = u.id
        WHERE m.id = {_LAST_ID}
    """)).fetchone()
    conn.close()
    return dict(msg) if msg else None


def get_message_with_reply(msg_id):
    """查询单条消息含引用信息，供 Socket.IO 广播用"""
    conn = get_conn()
    row = conn.execute(sql("""
        SELECT m.id, m.content, m.reply_to, m.image_url, m.created_at,
               u.nickname, u.id as user_id,
               rm.content as reply_content,
               rm.image_url as reply_image_url,
               ru.nickname as reply_nickname
        FROM messages m
        JOIN users u ON m.user_id = u.id
        LEFT JOIN messages rm ON m.reply_to = rm.id
        LEFT JOIN users ru ON rm.user_id = ru.id
        WHERE m.id = ?
    """), (msg_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# --- Line comment queries ---

def get_line_comments(song_id, line_index):
    conn = get_conn()
    rows = conn.execute(sql("""
        SELECT lc.id, lc.line_index, lc.line_text, lc.content, lc.created_at,
               u.nickname, u.id as user_id
        FROM line_comments lc JOIN users u ON lc.user_id = u.id
        WHERE lc.song_id = ? AND lc.line_index = ?
        ORDER BY lc.created_at DESC
    """), (song_id, line_index)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_line_comment(song_id, line_index, line_text, user_id, content):
    _NOW = now_expr()
    _LAST_ID = last_id_expr()
    conn = get_conn()
    conn.execute(
        sql(f"INSERT INTO line_comments (song_id, line_index, line_text, user_id, content, created_at) VALUES (?, ?, ?, ?, ?, {_NOW})"),
        (song_id, line_index, line_text, user_id, content)
    )
    conn.commit()
    row = conn.execute(sql(f"""
        SELECT lc.id, lc.line_index, lc.line_text, lc.content, lc.created_at,
               u.nickname, u.id as user_id
        FROM line_comments lc JOIN users u ON lc.user_id = u.id
        WHERE lc.id = {_LAST_ID}
    """)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_line_comments(song_id):
    conn = get_conn()
    rows = conn.execute(sql("""
        SELECT lc.id, lc.line_index, lc.line_text, lc.content, lc.created_at,
               u.nickname, u.id as user_id
        FROM line_comments lc JOIN users u ON lc.user_id = u.id
        WHERE lc.song_id = ?
        ORDER BY lc.line_index, lc.created_at DESC
    """), (song_id,)).fetchall()
    conn.close()
    # Group by line_index
    grouped = {}
    for r in rows:
        d = dict(r)
        idx = d['line_index']
        if idx not in grouped:
            grouped[idx] = []
        grouped[idx].append(d)
    return grouped
