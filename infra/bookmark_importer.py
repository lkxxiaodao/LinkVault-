"""浏览器收藏夹 HTML 导入模块"""
import re
import html
from data.database import get_connection
from data.bookmark_repo import BookmarkRepo
from data.folder_repo import FolderRepo

# 系统文件夹名称（不导入这些文件夹本身，但会导入其子内容）
_SYSTEM_FOLDERS = {
    '收藏夹栏', 'Bookmarks Bar', '其他书签', 'Other Bookmarks',
    '移动端书签', 'Mobile Bookmarks', '书签栏',
}


def parse_bookmark_html(filepath):
    """解析浏览器导出的 Netscape 书签 HTML 文件，返回 (folders, bookmarks) 层级结构"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 去掉 meta / title / h1 标签
    content = re.sub(r'<META[^>]*>', '', content, flags=re.IGNORECASE)
    content = re.sub(r'<TITLE>[^<]*</TITLE>', '', content, flags=re.IGNORECASE)
    content = re.sub(r'<H1>[^<]*</H1>', '', content, flags=re.IGNORECASE)

    folders = []
    bookmarks = []
    folder_id_stack = [None]  # 当前每个嵌套层级的临时文件夹索引

    # 按 <DT> 分割每个条目，同时用 </DL> 细分以正确追踪层级
    # 先按 <DT> 分割，再在每个条目内识别 </DL>
    raw_entries = re.split(r'<DT>', content)[1:]  # 去掉第一个空段

    entries = []
    for raw in raw_entries:
        # 在每个条目内部按 </DL> 拆分，让 </DL> 成为独立条目以正确弹栈
        parts = re.split(r'(</DL\s*>)', raw, flags=re.IGNORECASE)
        for part in parts:
            entries.append(part.strip())

    for entry in entries:
        if not entry:
            continue

        # 处理 </DL> 闭合标签
        if re.match(r'</DL\s*>', entry):
            if folder_id_stack:
                folder_id_stack.pop()
            continue

        # 匹配文件夹: <H3 ...>Name</H3>
        h3_match = re.match(r'<H3[^>]*>(.*?)</H3>', entry, re.DOTALL)
        if h3_match:
            name = html.unescape(h3_match.group(1).strip())
            parent_idx = folder_id_stack[-1] if folder_id_stack else None

            if name not in _SYSTEM_FOLDERS:
                folders.append({
                    'name': name,
                    'parent_idx': parent_idx,
                })
                folder_id_stack.append(len(folders) - 1)
            else:
                # 系统文件夹不创建，但子内容归到栈顶的 parent
                folder_id_stack.append(parent_idx)
            continue

        # 匹配书签: <A HREF="url" ...>Title</A>
        a_match = re.search(r'<A[^>]*HREF="([^"]*)"[^>]*>(.*?)</A>', entry, re.DOTALL | re.IGNORECASE)
        if a_match:
            url = html.unescape(a_match.group(1).strip())
            title = html.unescape(re.sub(r'<[^>]+>', '', a_match.group(2)).strip())
            if not title:
                title = url
            parent_idx = folder_id_stack[-1] if folder_id_stack else None
            bookmarks.append({'title': title, 'url': url, 'parent_idx': parent_idx})

    return folders, bookmarks


def import_bookmarks_from_html(filepath, progress_callback=None):
    """从浏览器导出的 HTML 文件导入收藏夹，返回 (imported_count, skipped_count)"""
    folders, bookmarks = parse_bookmark_html(filepath)

    # 第一步：创建文件夹，建立 临时索引 -> 真实 ID 的映射
    idx_to_real_id = {}
    for i, folder in enumerate(folders):
        parent_idx = folder['parent_idx']
        real_parent_id = idx_to_real_id.get(parent_idx) if parent_idx is not None else None

        existing = FolderRepo.get_by_name(folder['name'], real_parent_id)
        if existing:
            idx_to_real_id[i] = existing['id']
        else:
            fid = FolderRepo.create(folder['name'], real_parent_id)
            idx_to_real_id[i] = fid

    # 第二步：创建书签
    conn = get_connection()
    total = len(bookmarks)
    imported = 0
    skipped = 0

    try:
        for idx, bm in enumerate(bookmarks):
            if progress_callback:
                progress_callback(idx + 1, total)

            existing = BookmarkRepo.find_by_url(bm['url'])
            if existing:
                skipped += 1
                continue

            parent_idx = bm['parent_idx']
            real_parent_id = idx_to_real_id.get(parent_idx) if parent_idx is not None else None

            BookmarkRepo.create(bm['title'], bm['url'], real_parent_id)
            imported += 1
    finally:
        conn.close()

    return imported, skipped