from data.database import get_connection


class FolderRepo:
    @staticmethod
    def get_all():
        conn = get_connection()
        try:
            rows = conn.execute(
                'SELECT * FROM folders ORDER BY sort_order, name'
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_by_parent(parent_id):
        conn = get_connection()
        try:
            if parent_id is None:
                rows = conn.execute(
                    'SELECT * FROM folders WHERE parent_id IS NULL ORDER BY sort_order, name'
                ).fetchall()
            else:
                rows = conn.execute(
                    'SELECT * FROM folders WHERE parent_id = ? ORDER BY sort_order, name',
                    (parent_id,)
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_by_id(folder_id):
        conn = get_connection()
        try:
            row = conn.execute('SELECT * FROM folders WHERE id = ?', (folder_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def create(name, parent_id=None):
        conn = get_connection()
        try:
            cursor = conn.execute(
                'INSERT INTO folders (name, parent_id) VALUES (?, ?)',
                (name, parent_id)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    @staticmethod
    def update(folder_id, **kwargs):
        allowed = {'name', 'parent_id', 'sort_order'}
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return
        set_clause = ', '.join(f'{k} = ?' for k in fields)
        values = list(fields.values()) + [folder_id]
        conn = get_connection()
        try:
            conn.execute(
                f'UPDATE folders SET {set_clause}, updated_at = datetime(\'now\', \'localtime\') WHERE id = ?',
                values
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def delete(folder_id):
        conn = get_connection()
        try:
            conn.execute('DELETE FROM folders WHERE id = ?', (folder_id,))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def get_children_recursive(folder_id):
        conn = get_connection()
        try:
            ids = [folder_id]
            result = [folder_id]
            while ids:
                rows = conn.execute(
                    'SELECT id FROM folders WHERE parent_id IN ({})'.format(','.join('?' * len(ids))),
                    ids
                ).fetchall()
                ids = [r['id'] for r in rows]
                result.extend(ids)
            return result
        finally:
            conn.close()