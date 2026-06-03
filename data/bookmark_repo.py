from data.database import get_connection


class BookmarkRepo:
    @staticmethod
    def get_all():
        conn = get_connection()
        try:
            rows = conn.execute('SELECT * FROM bookmarks WHERE is_deleted = 0 ORDER BY title').fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_by_folder(folder_id):
        conn = get_connection()
        try:
            rows = conn.execute(
                'SELECT * FROM bookmarks WHERE folder_id = ? AND is_deleted = 0 ORDER BY title',
                (folder_id,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_by_id(bookmark_id):
        conn = get_connection()
        try:
            row = conn.execute('SELECT * FROM bookmarks WHERE id = ?', (bookmark_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def search(query):
        conn = get_connection()
        try:
            pattern = f'%{query}%'
            rows = conn.execute(
                '''SELECT DISTINCT b.* FROM bookmarks b
                   LEFT JOIN bookmark_tags bt ON b.id = bt.bookmark_id
                   LEFT JOIN tags t ON bt.tag_id = t.id
                   WHERE b.is_deleted = 0 AND (b.title LIKE ? OR b.url LIKE ? OR b.notes LIKE ? OR t.name LIKE ?)
                   ORDER BY b.title''',
                (pattern, pattern, pattern, pattern)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def find_by_url(url):
        conn = get_connection()
        try:
            row = conn.execute('SELECT * FROM bookmarks WHERE url = ? AND is_deleted = 0', (url,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def create(title, url, folder_id=None, default_browser=None, notes=''):
        conn = get_connection()
        try:
            cursor = conn.execute(
                'INSERT INTO bookmarks (title, url, folder_id, default_browser, notes) VALUES (?, ?, ?, ?, ?)',
                (title, url, folder_id, default_browser, notes)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    @staticmethod
    def update(bookmark_id, **kwargs):
        allowed = {'title', 'url', 'folder_id', 'default_browser', 'favicon_path', 'notes'}
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return
        set_clause = ', '.join(f'{k} = ?' for k in fields)
        values = list(fields.values()) + [bookmark_id]
        conn = get_connection()
        try:
            conn.execute(
                f'UPDATE bookmarks SET {set_clause}, updated_at = datetime(\'now\', \'localtime\') WHERE id = ?',
                values
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def record_click(bookmark_id):
        conn = get_connection()
        try:
            conn.execute(
                'UPDATE bookmarks SET click_count = COALESCE(click_count, 0) + 1, '
                'last_opened_at = datetime(\'now\', \'localtime\') WHERE id = ?',
                (bookmark_id,)
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def get_most_opened(limit=100):
        conn = get_connection()
        try:
            rows = conn.execute(
                'SELECT * FROM bookmarks WHERE is_deleted = 0 ORDER BY COALESCE(click_count, 0) DESC, title ASC LIMIT ?',
                (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_recently_opened(limit=100):
        conn = get_connection()
        try:
            rows = conn.execute(
                'SELECT * FROM bookmarks WHERE is_deleted = 0 ORDER BY last_opened_at DESC NULLS LAST, title ASC LIMIT ?',
                (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def reset_stats(bookmark_ids=None):
        conn = get_connection()
        try:
            if bookmark_ids:
                placeholders = ','.join('?' for _ in bookmark_ids)
                conn.execute(
                    f'UPDATE bookmarks SET click_count = 0, last_opened_at = NULL WHERE id IN ({placeholders})',
                    bookmark_ids
                )
            else:
                conn.execute('UPDATE bookmarks SET click_count = 0, last_opened_at = NULL')
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def delete(bookmark_id):
        conn = get_connection()
        try:
            conn.execute(
                'UPDATE bookmarks SET is_deleted = 1, deleted_at = datetime(\'now\', \'localtime\') WHERE id = ?',
                (bookmark_id,)
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def restore(bookmark_id):
        conn = get_connection()
        try:
            conn.execute(
                'UPDATE bookmarks SET is_deleted = 0, deleted_at = NULL WHERE id = ?',
                (bookmark_id,)
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def permanently_delete(bookmark_id):
        conn = get_connection()
        try:
            conn.execute('DELETE FROM bookmark_tags WHERE bookmark_id = ?', (bookmark_id,))
            conn.execute('DELETE FROM open_history WHERE bookmark_id = ?', (bookmark_id,))
            conn.execute('DELETE FROM pool_bookmarks WHERE bookmark_id = ?', (bookmark_id,))
            conn.execute('DELETE FROM bookmarks WHERE id = ?', (bookmark_id,))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def get_deleted():
        conn = get_connection()
        try:
            rows = conn.execute(
                'SELECT * FROM bookmarks WHERE is_deleted = 1 ORDER BY deleted_at DESC'
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def empty_trash():
        conn = get_connection()
        try:
            conn.execute(
                'DELETE FROM bookmark_tags WHERE bookmark_id IN (SELECT id FROM bookmarks WHERE is_deleted = 1)'
            )
            conn.execute(
                'DELETE FROM open_history WHERE bookmark_id IN (SELECT id FROM bookmarks WHERE is_deleted = 1)'
            )
            conn.execute(
                'DELETE FROM pool_bookmarks WHERE bookmark_id IN (SELECT id FROM bookmarks WHERE is_deleted = 1)'
            )
            conn.execute('DELETE FROM bookmarks WHERE is_deleted = 1')
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def move_to_folder(bookmark_id, folder_id):
        BookmarkRepo.update(bookmark_id, folder_id=folder_id)

    @staticmethod
    def get_tags(bookmark_id):
        conn = get_connection()
        try:
            rows = conn.execute(
                'SELECT t.id, t.name FROM tags t '
                'JOIN bookmark_tags bt ON t.id = bt.tag_id '
                'WHERE bt.bookmark_id = ? ORDER BY t.name',
                (bookmark_id,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def set_tags(bookmark_id, tag_names):
        conn = get_connection()
        try:
            conn.execute('DELETE FROM bookmark_tags WHERE bookmark_id = ?', (bookmark_id,))
            for name in tag_names:
                name = name.strip()
                if not name:
                    continue
                conn.execute('INSERT OR IGNORE INTO tags (name) VALUES (?)', (name,))
                row = conn.execute('SELECT id FROM tags WHERE name = ?', (name,)).fetchone()
                if row:
                    conn.execute(
                        'INSERT OR IGNORE INTO bookmark_tags (bookmark_id, tag_id) VALUES (?, ?)',
                        (bookmark_id, row['id'])
                    )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def get_all_tags():
        conn = get_connection()
        try:
            rows = conn.execute(
                'SELECT t.id, t.name, COUNT(bt.bookmark_id) as cnt FROM tags t '
                'LEFT JOIN bookmark_tags bt ON t.id = bt.tag_id '
                'LEFT JOIN bookmarks b ON bt.bookmark_id = b.id AND b.is_deleted = 0 '
                'GROUP BY t.id HAVING cnt > 0 ORDER BY t.name'
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_batch_tags(bookmark_ids):
        if not bookmark_ids:
            return {}
        conn = get_connection()
        try:
            placeholders = ','.join('?' for _ in bookmark_ids)
            rows = conn.execute(
                f'SELECT bt.bookmark_id, t.name FROM bookmark_tags bt '
                f'JOIN tags t ON bt.tag_id = t.id '
                f'WHERE bt.bookmark_id IN ({placeholders}) ORDER BY t.name',
                bookmark_ids
            ).fetchall()
            result = {}
            for r in rows:
                bm_id = r['bookmark_id']
                if bm_id not in result:
                    result[bm_id] = []
                result[bm_id].append(r['name'])
            return result
        finally:
            conn.close()

    @staticmethod
    def search_by_tag(tag_name):
        conn = get_connection()
        try:
            rows = conn.execute(
                'SELECT b.* FROM bookmarks b '
                'JOIN bookmark_tags bt ON b.id = bt.bookmark_id '
                'JOIN tags t ON bt.tag_id = t.id '
                'WHERE t.name = ? ORDER BY b.title',
                (tag_name,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def batch_delete(bookmark_ids):
        if not bookmark_ids:
            return
        conn = get_connection()
        try:
            placeholders = ','.join('?' for _ in bookmark_ids)
            conn.execute(
                f'UPDATE bookmarks SET is_deleted = 1, deleted_at = datetime(\'now\', \'localtime\') '
                f'WHERE id IN ({placeholders})',
                bookmark_ids
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def batch_update(bookmark_ids, **kwargs):
        if not bookmark_ids or not kwargs:
            return
        allowed = {'title', 'url', 'folder_id', 'default_browser', 'favicon_path', 'notes'}
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return
        set_clause = ', '.join(f'{k} = ?' for k in fields)
        values = list(fields.values())
        placeholders = ','.join('?' for _ in bookmark_ids)
        values.extend(bookmark_ids)
        conn = get_connection()
        try:
            conn.execute(
                f'UPDATE bookmarks SET {set_clause}, updated_at = datetime(\'now\', \'localtime\') '
                f'WHERE id IN ({placeholders})',
                values
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def batch_add_tags(bookmark_ids, tag_names):
        if not bookmark_ids or not tag_names:
            return
        conn = get_connection()
        try:
            for name in tag_names:
                name = name.strip()
                if not name:
                    continue
                conn.execute('INSERT OR IGNORE INTO tags (name) VALUES (?)', (name,))
                row = conn.execute('SELECT id FROM tags WHERE name = ?', (name,)).fetchone()
                if not row:
                    continue
                tag_id = row['id']
                for bm_id in bookmark_ids:
                    conn.execute(
                        'INSERT OR IGNORE INTO bookmark_tags (bookmark_id, tag_id) VALUES (?, ?)',
                        (bm_id, tag_id)
                    )
            conn.commit()
        finally:
            conn.close()