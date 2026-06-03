from data.database import get_connection


class ScheduleRepo:
    @staticmethod
    def get_all():
        conn = get_connection()
        try:
            rows = conn.execute('SELECT * FROM schedules ORDER BY created_at').fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_active():
        conn = get_connection()
        try:
            rows = conn.execute('SELECT * FROM schedules WHERE is_active = 1').fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_by_id(schedule_id):
        conn = get_connection()
        try:
            row = conn.execute('SELECT * FROM schedules WHERE id = ?', (schedule_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def create(name, hour, minute, repeat_type, repeat_days=None):
        conn = get_connection()
        try:
            cursor = conn.execute(
                'INSERT INTO schedules (name, hour, minute, repeat_type, repeat_days) VALUES (?, ?, ?, ?, ?)',
                (name, hour, minute, repeat_type, repeat_days)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    @staticmethod
    def update(schedule_id, **kwargs):
        allowed = {'name', 'hour', 'minute', 'repeat_type', 'repeat_days', 'is_active'}
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return
        set_clause = ', '.join(f'{k} = ?' for k in fields)
        values = list(fields.values()) + [schedule_id]
        conn = get_connection()
        try:
            conn.execute(f'UPDATE schedules SET {set_clause} WHERE id = ?', values)
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def delete(schedule_id):
        conn = get_connection()
        try:
            conn.execute('DELETE FROM schedules WHERE id = ?', (schedule_id,))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def get_bookmarks(schedule_id):
        conn = get_connection()
        try:
            rows = conn.execute(
                '''SELECT b.* FROM bookmarks b
                   JOIN schedule_bookmarks sb ON b.id = sb.bookmark_id
                   WHERE sb.schedule_id = ?
                   ORDER BY sb.sort_order''',
                (schedule_id,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def add_bookmark(schedule_id, bookmark_id, sort_order=0):
        conn = get_connection()
        try:
            conn.execute(
                'INSERT OR IGNORE INTO schedule_bookmarks (schedule_id, bookmark_id, sort_order) VALUES (?, ?, ?)',
                (schedule_id, bookmark_id, sort_order)
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def remove_bookmark(schedule_id, bookmark_id):
        conn = get_connection()
        try:
            conn.execute(
                'DELETE FROM schedule_bookmarks WHERE schedule_id = ? AND bookmark_id = ?',
                (schedule_id, bookmark_id)
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def set_bookmarks(schedule_id, bookmark_ids):
        conn = get_connection()
        try:
            conn.execute('DELETE FROM schedule_bookmarks WHERE schedule_id = ?', (schedule_id,))
            for i, bid in enumerate(bookmark_ids):
                conn.execute(
                    'INSERT OR IGNORE INTO schedule_bookmarks (schedule_id, bookmark_id, sort_order) VALUES (?, ?, ?)',
                    (schedule_id, bid, i)
                )
            conn.commit()
        finally:
            conn.close()