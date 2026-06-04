from data.bookmark_repo import BookmarkRepo
from data.history_repo import HistoryRepo


class BookmarkManager:
    @staticmethod
    def add_bookmark(title, url, folder_id=None, default_browser=None, notes=''):
        bookmark_id = BookmarkRepo.create(title, url, folder_id, default_browser, notes)
        return bookmark_id

    @staticmethod
    def update_bookmark(bookmark_id, **kwargs):
        BookmarkRepo.update(bookmark_id, **kwargs)

    @staticmethod
    def delete_bookmark(bookmark_id):
        BookmarkRepo.delete(bookmark_id)

    @staticmethod
    def search(query):
        return BookmarkRepo.search(query)

    @staticmethod
    def get_by_folder(folder_id):
        return BookmarkRepo.get_by_folder(folder_id)

    @staticmethod
    def get_all():
        return BookmarkRepo.get_all()

    @staticmethod
    def get_by_id(bookmark_id):
        return BookmarkRepo.get_by_id(bookmark_id)

    @staticmethod
    def find_by_url(url):
        return BookmarkRepo.find_by_url(url)

    @staticmethod
    def get_tags(bookmark_id):
        return BookmarkRepo.get_tags(bookmark_id)

    @staticmethod
    def set_tags(bookmark_id, tag_names):
        BookmarkRepo.set_tags(bookmark_id, tag_names)

    @staticmethod
    def get_all_tags():
        return BookmarkRepo.get_all_tags()

    @staticmethod
    def get_batch_tags(bookmark_ids):
        return BookmarkRepo.get_batch_tags(bookmark_ids)

    @staticmethod
    def search_by_tag(tag_name):
        return BookmarkRepo.search_by_tag(tag_name)

    @staticmethod
    def batch_delete(bookmark_ids):
        BookmarkRepo.batch_delete(bookmark_ids)

    @staticmethod
    def batch_update(bookmark_ids, **kwargs):
        BookmarkRepo.batch_update(bookmark_ids, **kwargs)

    @staticmethod
    def batch_move_to_folder(bookmark_ids, folder_id):
        BookmarkRepo.batch_update(bookmark_ids, folder_id=folder_id)

    @staticmethod
    def batch_add_tags(bookmark_ids, tag_names):
        BookmarkRepo.batch_add_tags(bookmark_ids, tag_names)

    @staticmethod
    def open_in_browser(bookmark_id, browser=None):
        bookmark = BookmarkRepo.get_by_id(bookmark_id)
        if not bookmark:
            return
        from infra.browser_launcher import BrowserLauncher
        BrowserLauncher.open_url(bookmark['url'], browser or bookmark.get('default_browser'))
        HistoryRepo.record(bookmark_id, 'manual')
        BookmarkRepo.record_click(bookmark_id)

    @staticmethod
    def get_most_opened(limit=100):
        return BookmarkRepo.get_most_opened(limit)

    @staticmethod
    def get_recently_opened(limit=100):
        return BookmarkRepo.get_recently_opened(limit)

    @staticmethod
    def reset_stats(bookmark_ids=None):
        BookmarkRepo.reset_stats(bookmark_ids)

    @staticmethod
    def get_deleted():
        return BookmarkRepo.get_deleted()

    @staticmethod
    def restore_bookmark(bookmark_id):
        BookmarkRepo.restore(bookmark_id)

    @staticmethod
    def permanently_delete(bookmark_id):
        BookmarkRepo.permanently_delete(bookmark_id)

    @staticmethod
    def empty_trash():
        BookmarkRepo.empty_trash()