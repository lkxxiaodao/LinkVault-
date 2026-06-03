from data.database import get_connection


class PoolRepo:
    @staticmethod
    def get_all():
        conn = get_connection()
        try:
            rows = conn.execute('SELECT * FROM random_pools ORDER BY created_at').fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_by_id(pool_id):
        conn = get_connection()
        try:
            row = conn.execute('SELECT * FROM random_pools WHERE id = ?', (pool_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_active():
        conn = get_connection()
        try:
            row = conn.execute('SELECT * FROM random_pools WHERE is_active = 1').fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def create(name):
        conn = get_connection()
        try:
            cursor = conn.execute('INSERT INTO random_pools (name) VALUES (?)', (name,))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    @staticmethod
    def update(pool_id, **kwargs):
        allowed = {'name', 'is_active'}
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return
        set_clause = ', '.join(f'{k} = ?' for k in fields)
        values = list(fields.values()) + [pool_id]
        conn = get_connection()
        try:
            conn.execute(f'UPDATE random_pools SET {set_clause} WHERE id = ?', values)
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def delete(pool_id):
        conn = get_connection()
        try:
            conn.execute('DELETE FROM random_pools WHERE id = ?', (pool_id,))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def set_active(pool_id):
        conn = get_connection()
        try:
            conn.execute('UPDATE random_pools SET is_active = 0')
            if pool_id is not None:
                conn.execute('UPDATE random_pools SET is_active = 1 WHERE id = ?', (pool_id,))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def get_bookmarks(pool_id):
        conn = get_connection()
        try:
            rows = conn.execute(
                '''SELECT b.* FROM bookmarks b
                   JOIN pool_bookmarks pb ON b.id = pb.bookmark_id
                   WHERE pb.pool_id = ?''',
                (pool_id,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def add_bookmark(pool_id, bookmark_id):
        conn = get_connection()
        try:
            conn.execute(
                'INSERT OR IGNORE INTO pool_bookmarks (pool_id, bookmark_id) VALUES (?, ?)',
                (pool_id, bookmark_id)
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def remove_bookmark(pool_id, bookmark_id):
        conn = get_connection()
        try:
            conn.execute(
                'DELETE FROM pool_bookmarks WHERE pool_id = ? AND bookmark_id = ?',
                (pool_id, bookmark_id)
            )
            conn.commit()
        finally:
            conn.close()