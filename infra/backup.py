import json
import os
from data.database import get_connection
from data.bookmark_repo import BookmarkRepo
from data.folder_repo import FolderRepo
from data.schedule_repo import ScheduleRepo
from data.pool_repo import PoolRepo
from infra.encryption import encrypt_data, decrypt_data


class BackupManager:
    @staticmethod
    def _get_filtered_bookmark_ids(folder_ids=None, tag_names=None):
        """根据文件夹ID列表或标签名称列表获取过滤后的书签ID集合"""
        ids = set()
        conn = get_connection()
        try:
            if folder_ids:
                all_folder_ids = set()
                for fid in folder_ids:
                    all_folder_ids.add(fid)
                    all_folder_ids.update(FolderRepo.get_children_recursive(fid))
                placeholders = ','.join('?' * len(all_folder_ids))
                rows = conn.execute(
                    f'SELECT id FROM bookmarks WHERE folder_id IN ({placeholders})',
                    list(all_folder_ids)
                ).fetchall()
                ids.update(r['id'] for r in rows)
            if tag_names:
                placeholders = ','.join('?' * len(tag_names))
                rows = conn.execute(
                    f'SELECT DISTINCT b.id FROM bookmarks b '
                    f'JOIN bookmark_tags bt ON b.id = bt.bookmark_id '
                    f'JOIN tags t ON bt.tag_id = t.id '
                    f'WHERE t.name IN ({placeholders})',
                    list(tag_names)
                ).fetchall()
                ids.update(r['id'] for r in rows)
        finally:
            conn.close()
        return ids

    @staticmethod
    def export_linkvault(filepath, password, folder_ids=None, tag_names=None):
        conn = get_connection()
        folders = [dict(r) for r in conn.execute('SELECT * FROM folders').fetchall()]
        bookmarks = [dict(r) for r in conn.execute('SELECT * FROM bookmarks').fetchall()]
        schedules = [dict(r) for r in conn.execute('SELECT * FROM schedules').fetchall()]
        sched_bms = [dict(r) for r in conn.execute('SELECT * FROM schedule_bookmarks').fetchall()]
        pools = [dict(r) for r in conn.execute('SELECT * FROM random_pools').fetchall()]
        pool_bms = [dict(r) for r in conn.execute('SELECT * FROM pool_bookmarks').fetchall()]
        settings_data = [dict(r) for r in conn.execute('SELECT * FROM settings').fetchall()]
        tags_data = [dict(r) for r in conn.execute('SELECT * FROM tags').fetchall()]
        bookmark_tags_data = [dict(r) for r in conn.execute('SELECT * FROM bookmark_tags').fetchall()]
        conn.close()

        filtered_ids = BackupManager._get_filtered_bookmark_ids(folder_ids, tag_names)
        if filtered_ids:
            bookmarks = [b for b in bookmarks if b['id'] in filtered_ids]
            bookmark_tags_data = [bt for bt in bookmark_tags_data if bt['bookmark_id'] in filtered_ids]
            sched_bms = [sb for sb in sched_bms if sb['bookmark_id'] in filtered_ids]
            pool_bms = [pb for pb in pool_bms if pb['bookmark_id'] in filtered_ids]

        data = {
            'version': 1,
            'folders': folders,
            'bookmarks': bookmarks,
            'schedules': schedules,
            'schedule_bookmarks': sched_bms,
            'random_pools': pools,
            'pool_bookmarks': pool_bms,
            'settings': settings_data,
            'tags': tags_data,
            'bookmark_tags': bookmark_tags_data,
        }

        encrypted = encrypt_data(data, password)
        with open(filepath, 'wb') as f:
            f.write(encrypted)

    @staticmethod
    def import_linkvault(filepath, password):
        with open(filepath, 'rb') as f:
            raw = f.read()
        data = decrypt_data(raw, password)
        conn = get_connection()

        for f_data in data.get('folders', []):
            conn.execute(
                'INSERT OR REPLACE INTO folders (id, name, parent_id, sort_order, created_at, updated_at) '
                'VALUES (?, ?, ?, ?, ?, ?)',
                (f_data['id'], f_data['name'], f_data.get('parent_id'), f_data.get('sort_order', 0),
                 f_data.get('created_at'), f_data.get('updated_at'))
            )

        for b_data in data.get('bookmarks', []):
            conn.execute(
                'INSERT OR REPLACE INTO bookmarks (id, folder_id, title, url, favicon_path, '
                'default_browser, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (b_data['id'], b_data.get('folder_id'), b_data['title'], b_data['url'],
                 b_data.get('favicon_path'), b_data.get('default_browser'),
                 b_data.get('created_at'), b_data.get('updated_at'))
            )

        for s_data in data.get('schedules', []):
            conn.execute(
                'INSERT OR REPLACE INTO schedules (id, name, hour, minute, repeat_type, '
                'repeat_days, is_active, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (s_data['id'], s_data['name'], s_data['hour'], s_data['minute'],
                 s_data['repeat_type'], s_data.get('repeat_days'),
                 s_data.get('is_active', 1), s_data.get('created_at'))
            )

        for sb_data in data.get('schedule_bookmarks', []):
            conn.execute(
                'INSERT OR IGNORE INTO schedule_bookmarks (schedule_id, bookmark_id, sort_order) '
                'VALUES (?, ?, ?)',
                (sb_data['schedule_id'], sb_data['bookmark_id'], sb_data.get('sort_order', 0))
            )

        for p_data in data.get('random_pools', []):
            conn.execute(
                'INSERT OR REPLACE INTO random_pools (id, name, is_active, created_at) '
                'VALUES (?, ?, ?, ?)',
                (p_data['id'], p_data['name'], p_data.get('is_active', 0), p_data.get('created_at'))
            )

        for pb_data in data.get('pool_bookmarks', []):
            conn.execute(
                'INSERT OR IGNORE INTO pool_bookmarks (pool_id, bookmark_id) VALUES (?, ?)',
                (pb_data['pool_id'], pb_data['bookmark_id'])
            )

        for s_data in data.get('settings', []):
            conn.execute(
                'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
                (s_data['key'], s_data['value'])
            )

        for t_data in data.get('tags', []):
            conn.execute(
                'INSERT OR IGNORE INTO tags (id, name, created_at) VALUES (?, ?, ?)',
                (t_data['id'], t_data['name'], t_data.get('created_at'))
            )
        for bt_data in data.get('bookmark_tags', []):
            conn.execute(
                'INSERT OR IGNORE INTO bookmark_tags (bookmark_id, tag_id) VALUES (?, ?)',
                (bt_data['bookmark_id'], bt_data['tag_id'])
            )

        conn.commit()
        conn.close()

    @staticmethod
    def export_html(filepath, folder_ids=None, tag_names=None):
        bookmarks = BookmarkRepo.get_all()
        folders = {f['id']: f for f in FolderRepo.get_all()}

        filtered_ids = BackupManager._get_filtered_bookmark_ids(folder_ids, tag_names)

        folder_map = {}
        root_ids = []
        for f in folders.values():
            pid = f.get('parent_id')
            if pid is None:
                root_ids.append(f['id'])
            else:
                folder_map.setdefault(pid, []).append(f['id'])

        bm_by_folder = {}
        for bm in bookmarks:
            if filtered_ids and bm['id'] not in filtered_ids:
                continue
            fid = bm.get('folder_id')
            bm_by_folder.setdefault(fid, []).append(bm)

        html = [
            '<!DOCTYPE NETSCAPE-Bookmark-file-1>',
            '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
            '<TITLE>LinkVault Bookmarks</TITLE>',
            '<H1>LinkVault Bookmarks</H1>',
            '<DL><p>',
        ]

        def render_folder(fid, depth):
            lines = []
            f = folders.get(fid)
            if f:
                lines.append(f'{"    " * depth}<DT><H3>{_esc(f["name"])}</H3>')
                lines.append(f'{"    " * depth}<DL><p>')
                for bm in bm_by_folder.get(fid, []):
                    lines.append(f'{"    " * (depth + 1)}<DT><A HREF="{_esc(bm["url"])}">{_esc(bm["title"])}</A>')
                for child_id in folder_map.get(fid, []):
                    lines.extend(render_folder(child_id, depth + 1))
                lines.append(f'{"    " * depth}</DL><p>')
            return lines

        for root_id in root_ids:
            html.extend(render_folder(root_id, 0))

        for bm in bm_by_folder.get(None, []):
            html.append(f'    <DT><A HREF="{_esc(bm["url"])}">{_esc(bm["title"])}</A>')

        html.append('</DL><p>')

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(html))


def _esc(text):
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')