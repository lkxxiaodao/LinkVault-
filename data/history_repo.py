from data.database import get_connection


class HistoryRepo:
    @staticmethod
    def record(bookmark_id, opened_via='manual'):
        conn = get_connection()
        try:
            conn.execute(
                'INSERT INTO open_history (bookmark_id, opened_via) VALUES (?, ?)',
                (bookmark_id, opened_via)
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def get_by_bookmark(bookmark_id, days=30):
        conn = get_connection()
        try:
            rows = conn.execute(
                '''SELECT * FROM open_history
                   WHERE bookmark_id = ?
                   AND opened_at >= datetime('now', 'localtime', ?)
                   ORDER BY opened_at DESC''',
                (bookmark_id, f'-{days} days')
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_recent(days=30):
        conn = get_connection()
        try:
            rows = conn.execute(
                '''SELECT * FROM open_history
                   WHERE opened_at >= datetime('now', 'localtime', ?)
                   ORDER BY opened_at DESC''',
                (f'-{days} days',)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()