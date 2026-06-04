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

    @staticmethod
    def get_bookmark_ids(folder_id):
        """获取文件夹及其所有子文件夹下的所有书签 ID（不含已删除）"""
        conn = get_connection()
        try:
            folder_ids = FolderRepo.get_children_recursive(folder_id)
            placeholders = ','.join('?' * len(folder_ids))
            rows = conn.execute(
                f'SELECT id FROM bookmarks WHERE folder_id IN ({placeholders}) AND is_deleted = 0',
                folder_ids
            ).fetchall()
            return [r['id'] for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_all_bookmark_folder_ids():
        """返回 {bookmark_id: folder_id} 映射（仅未删除书签），用于批量池状态检测"""
        conn = get_connection()
        try:
            rows = conn.execute(
                'SELECT id, folder_id FROM bookmarks WHERE is_deleted = 0 AND folder_id IS NOT NULL'
            ).fetchall()
            result = {}
            for r in rows:
                result[r['id']] = r['folder_id']
            return result
        finally:
            conn.close()

    @staticmethod
    def get_descendant_folder_ids(folder_ids, all_folders=None):
        """给定一组文件夹 ID，返回它们及其所有后代文件夹 ID 的集合。
        如果传入 all_folders 列表，可避免额外 DB 查询。"""
        if not folder_ids:
            return set()
        if all_folders is None:
            all_folders = FolderRepo.get_all()
        # 构建 parent_id -> [child_id, ...] 映射
        children_map = {}
        for f in all_folders:
            pid = f.get('parent_id')
            if pid not in children_map:
                children_map[pid] = []
            children_map[pid].append(f['id'])
        # BFS 收集所有后代
        result = set(folder_ids)
        queue = list(folder_ids)
        while queue:
            fid = queue.pop(0)
            for child in children_map.get(fid, []):
                if child not in result:
                    result.add(child)
                    queue.append(child)
        return result