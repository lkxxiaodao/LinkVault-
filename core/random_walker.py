import random
from data.pool_repo import PoolRepo
from data.bookmark_repo import BookmarkRepo
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