import random
from data.pool_repo import PoolRepo
from data.bookmark_repo import BookmarkRepo
from data.folder_repo import FolderRepo
from data.history_repo import HistoryRepo
from infra.browser_launcher import BrowserLauncher


class RandomWalker:
    @staticmethod
    def set_active_pool(pool_id):
        PoolRepo.set_active(pool_id)

    @staticmethod
    def get_active_pool():
        return PoolRepo.get_active()

    @staticmethod
    def walk():
        pool = PoolRepo.get_active()
        if not pool:
            return None
        bookmarks = PoolRepo.get_bookmarks(pool['id'])
        if not bookmarks:
            return None
        chosen = random.choice(bookmarks)
        BrowserLauncher.open_url(chosen['url'], chosen.get('default_browser'))
        HistoryRepo.record(chosen['id'], 'random')
        BookmarkRepo.record_click(chosen['id'])
        return chosen

    @staticmethod
    def create_pool(name):
        return PoolRepo.create(name)

    @staticmethod
    def delete_pool(pool_id):
        PoolRepo.delete(pool_id)

    @staticmethod
    def get_all_pools():
        return PoolRepo.get_all()

    @staticmethod
    def add_to_pool(pool_id, bookmark_id):
        PoolRepo.add_bookmark(pool_id, bookmark_id)

    @staticmethod
    def remove_from_pool(pool_id, bookmark_id):
        PoolRepo.remove_bookmark(pool_id, bookmark_id)

    @staticmethod
    def get_pool_bookmarks(pool_id):
        return PoolRepo.get_bookmarks(pool_id)

    @staticmethod
    def add_folder_to_pool(pool_id, folder_id):
        """将文件夹及其子文件夹下的所有书签加入随机池"""
        bookmark_ids = FolderRepo.get_bookmark_ids(folder_id)
        for bm_id in bookmark_ids:
            PoolRepo.add_bookmark(pool_id, bm_id)

    @staticmethod
    def remove_folder_from_pool(pool_id, folder_id):
        """将文件夹及其子文件夹下的所有书签移出随机池"""
        bookmark_ids = FolderRepo.get_bookmark_ids(folder_id)
        for bm_id in bookmark_ids:
            PoolRepo.remove_bookmark(pool_id, bm_id)

    @staticmethod
    def is_folder_in_pool(pool_id, folder_id):
        """检查文件夹下的所有书签是否都在池中（全部在才返回 True）"""
        bookmark_ids = FolderRepo.get_bookmark_ids(folder_id)
        if not bookmark_ids:
            return False
        pool_bookmarks = PoolRepo.get_bookmarks(pool_id)
        pool_ids = {b['id'] for b in pool_bookmarks}
        return all(bm_id in pool_ids for bm_id in bookmark_ids)

    @staticmethod
    def is_folder_partially_in_pool(pool_id, folder_id):
        """检查文件夹下是否有部分书签在池中"""
        bookmark_ids = FolderRepo.get_bookmark_ids(folder_id)
        if not bookmark_ids:
            return False
        pool_bookmarks = PoolRepo.get_bookmarks(pool_id)
        pool_ids = {b['id'] for b in pool_bookmarks}
        in_pool = sum(1 for bm_id in bookmark_ids if bm_id in pool_ids)
        return 0 < in_pool < len(bookmark_ids)