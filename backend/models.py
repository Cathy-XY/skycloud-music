import re
import os
import tempfile
from database import get_db
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
    conn = get_db()
    for fname in os.listdir(MUSIC_DIR):
        if not fname.lower().endswith('.mp3'):
            continue
        existing = conn.execute("SELECT id FROM songs WHERE filename = ?", (fname,)).fetchone()
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
                "INSERT INTO songs (title, artist, filename, duration) VALUES (?, ?, ?, ?)",
                (title, artist, fname, duration)
            )
            row = conn.execute("SELECT id FROM songs WHERE filename = ?", (fname,)).fetchone()
            song_id = row['id']
        has_lyrics = conn.execute("SELECT id FROM lyrics WHERE song_id = ?", (song_id,)).fetchone()
        if not has_lyrics:
            lrc = extract_lrc_from_mp3(os.path.join(MUSIC_DIR, fname))
            if lrc:
                conn.execute(
                    "INSERT INTO lyrics (song_id, content) VALUES (?, ?)",
                    (song_id, lrc)
                )
    conn.commit()
    conn.close()


def _scan_songs_cloud():
    from storage import list_cloud_songs, download_from_cloud
    filenames = list_cloud_songs()
    conn = get_db()
    for fname in filenames:
        existing = conn.execute("SELECT id FROM songs WHERE filename = ?", (fname,)).fetchone()
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
                "INSERT INTO songs (title, artist, filename, duration) VALUES (?, ?, ?, ?)",
                (title, artist, fname, duration)
            )
            row = conn.execute("SELECT id FROM songs WHERE filename = ?", (fname,)).fetchone()
            song_id = row['id']
        has_lyrics = conn.execute("SELECT id FROM lyrics WHERE song_id = ?", (song_id,)).fetchone()
        if not has_lyrics:
            tmp_path = os.path.join(tempfile.gettempdir(), 'cloud_scan', fname)
            if not os.path.exists(tmp_path):
                try:
                    download_from_cloud(fname, tmp_path)
                except Exception:
                    continue
            lrc = extract_lrc_from_mp3(tmp_path)
            if lrc:
                conn.execute(
                    "INSERT INTO lyrics (song_id, content) VALUES (?, ?)",
                    (song_id, lrc)
                )
    conn.commit()
    conn.close()


def extract_lrc_from_mp3(filepath):
    try:
        from mutagen.id3 import ID3
        tags = ID3(filepath)
        # Check standard USLT tag first
        for key in tags:
            if key.startswith('USLT'):
                text = str(tags[key])
                if '[' in text and ']' in text:
                    return text
        # Check non-standard TEXT tag (some files put LRC here)
        if 'TEXT' in tags:
            text = str(tags['TEXT'])
            if '[' in text and ']' in text:
                return text
    except Exception:
        pass
    return None


# --- User queries ---

def create_user(username, password_hash, nickname):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username, password, nickname) VALUES (?, ?, ?)",
            (username, password_hash, nickname)
        )
        conn.commit()
        user = conn.execute("SELECT id, username, nickname FROM users WHERE username = ?", (username,)).fetchone()
        return dict(user)
    finally:
        conn.close()


def get_user_by_username(username):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return dict(user) if user else None


def get_user_by_id(user_id):
    conn = get_db()
    user = conn.execute("SELECT id, username, nickname, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None


# --- Song queries ---

def get_all_songs():
    conn = get_db()
    songs = conn.execute("SELECT id, title, artist, filename, duration, created_at FROM songs ORDER BY id").fetchall()
    conn.close()
    return [dict(s) for s in songs]


def get_song_by_id(song_id):
    conn = get_db()
    song = conn.execute("SELECT * FROM songs WHERE id = ?", (song_id,)).fetchone()
    conn.close()
    return dict(song) if song else None


# --- Comment queries ---

def get_comments_by_song(song_id, page=1, per_page=20):
    conn = get_db()
    offset = (page - 1) * per_page
    comments = conn.execute("""
        SELECT c.id, c.content, c.created_at, u.nickname, u.id as user_id
        FROM comments c JOIN users u ON c.user_id = u.id
        WHERE c.song_id = ?
        ORDER BY c.created_at DESC
        LIMIT ? OFFSET ?
    """, (song_id, per_page, offset)).fetchall()
    conn.close()
    return [dict(c) for c in comments]


def create_comment(song_id, user_id, content):
    conn = get_db()
    conn.execute("INSERT INTO comments (song_id, user_id, content) VALUES (?, ?, ?)",
                 (song_id, user_id, content))
    conn.commit()
    comment = conn.execute("""
        SELECT c.id, c.content, c.created_at, u.nickname, u.id as user_id
        FROM comments c JOIN users u ON c.user_id = u.id
        WHERE c.id = last_insert_rowid()
    """).fetchone()
    conn.close()
    return dict(comment) if comment else None


def delete_comment(comment_id, user_id):
    conn = get_db()
    result = conn.execute("DELETE FROM comments WHERE id = ? AND user_id = ?", (comment_id, user_id))
    conn.commit()
    deleted = result.rowcount > 0
    conn.close()
    return deleted


# --- Lyrics queries ---

def get_lyrics(song_id):
    conn = get_db()
    row = conn.execute("""
        SELECT l.content, l.updated_at, u.nickname as edited_by_name
        FROM lyrics l LEFT JOIN users u ON l.edited_by = u.id
        WHERE l.song_id = ?
    """, (song_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def save_lyrics(song_id, user_id, content):
    conn = get_db()
    existing = conn.execute("SELECT id FROM lyrics WHERE song_id = ?", (song_id,)).fetchone()
    if existing:
        conn.execute(
            "UPDATE lyrics SET content = ?, edited_by = ?, updated_at = datetime('now') WHERE song_id = ?",
            (content, user_id, song_id)
        )
    else:
        conn.execute(
            "INSERT INTO lyrics (song_id, content, edited_by) VALUES (?, ?, ?)",
            (song_id, content, user_id)
        )
    conn.execute(
        "INSERT INTO lyrics_history (song_id, user_id, content) VALUES (?, ?, ?)",
        (song_id, user_id, content)
    )
    conn.commit()
    conn.close()


def get_lyrics_history(song_id):
    conn = get_db()
    rows = conn.execute("""
        SELECT lh.content, lh.created_at, u.nickname
        FROM lyrics_history lh JOIN users u ON lh.user_id = u.id
        WHERE lh.song_id = ?
        ORDER BY lh.created_at DESC
        LIMIT 20
    """, (song_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- Message queries ---

def get_messages(page=1, per_page=50):
    conn = get_db()
    offset = (page - 1) * per_page
    msgs = conn.execute("""
        SELECT m.id, m.content, m.created_at, u.nickname, u.id as user_id
        FROM messages m JOIN users u ON m.user_id = u.id
        ORDER BY m.created_at DESC
        LIMIT ? OFFSET ?
    """, (per_page, offset)).fetchall()
    conn.close()
    return [dict(m) for m in msgs]


def create_message(user_id, content):
    conn = get_db()
    conn.execute("INSERT INTO messages (user_id, content) VALUES (?, ?)", (user_id, content))
    conn.commit()
    msg = conn.execute("""
        SELECT m.id, m.content, m.created_at, u.nickname, u.id as user_id
        FROM messages m JOIN users u ON m.user_id = u.id
        WHERE m.id = last_insert_rowid()
    """).fetchone()
    conn.close()
    return dict(msg) if msg else None


# --- Line comment queries ---

def get_line_comments(song_id, line_index):
    conn = get_db()
    rows = conn.execute("""
        SELECT lc.id, lc.line_index, lc.line_text, lc.content, lc.created_at,
               u.nickname, u.id as user_id
        FROM line_comments lc JOIN users u ON lc.user_id = u.id
        WHERE lc.song_id = ? AND lc.line_index = ?
        ORDER BY lc.created_at DESC
    """, (song_id, line_index)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_line_comment(song_id, line_index, line_text, user_id, content):
    conn = get_db()
    conn.execute(
        "INSERT INTO line_comments (song_id, line_index, line_text, user_id, content) VALUES (?, ?, ?, ?, ?)",
        (song_id, line_index, line_text, user_id, content)
    )
    conn.commit()
    row = conn.execute("""
        SELECT lc.id, lc.line_index, lc.line_text, lc.content, lc.created_at,
               u.nickname, u.id as user_id
        FROM line_comments lc JOIN users u ON lc.user_id = u.id
        WHERE lc.id = last_insert_rowid()
    """).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_line_comments(song_id):
    conn = get_db()
    rows = conn.execute("""
        SELECT lc.id, lc.line_index, lc.line_text, lc.content, lc.created_at,
               u.nickname, u.id as user_id
        FROM line_comments lc JOIN users u ON lc.user_id = u.id
        WHERE lc.song_id = ?
        ORDER BY lc.line_index, lc.created_at DESC
    """, (song_id,)).fetchall()
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
