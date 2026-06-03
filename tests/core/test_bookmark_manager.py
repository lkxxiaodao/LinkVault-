from tests.core.base import BaseCoreTest
from core.bookmark_manager import BookmarkManager
from data.bookmark_repo import BookmarkRepo


class TestBookmarkManager(BaseCoreTest):
    def test_add_bookmark_returns_positive_id(self):
        bid = BookmarkManager.add_bookmark('Test', 'https://example.com')
        self.assertGreater(bid, 0)

    def test_add_bookmark_with_folder(self):
        fid = self._create_folder('Work')
        bid = BookmarkManager.add_bookmark('Work Site', 'https://work.com', folder_id=fid)
        bm = BookmarkRepo.get_by_id(bid)
        self.assertEqual(bm['folder_id'], fid)

    def test_add_bookmark_with_browser(self):
        bid = BookmarkManager.add_bookmark('Test', 'https://example.com', default_browser='chrome.exe')
        bm = BookmarkRepo.get_by_id(bid)
        self.assertEqual(bm['default_browser'], 'chrome.exe')

    def test_update_bookmark(self):
        bid = BookmarkManager.add_bookmark('Old', 'https://old.com')
        BookmarkManager.update_bookmark(bid, title='New', url='https://new.com')
        bm = BookmarkRepo.get_by_id(bid)
        self.assertEqual(bm['title'], 'New')
        self.assertEqual(bm['url'], 'https://new.com')

    def test_delete_bookmark(self):
        bid = BookmarkManager.add_bookmark('Delete Me', 'https://delete.com')
        BookmarkManager.delete_bookmark(bid)
        self.assertIsNone(BookmarkRepo.get_by_id(bid))

    def test_move_to_folder(self):
        fid1 = self._create_folder('A')
        fid2 = self._create_folder('B')
        bid = BookmarkManager.add_bookmark('Move', 'https://move.com', folder_id=fid1)
        BookmarkManager.move_to_folder(bid, fid2)
        bm = BookmarkRepo.get_by_id(bid)
        self.assertEqual(bm['folder_id'], fid2)

    def test_search(self):
        BookmarkManager.add_bookmark('Python Guide', 'https://py.com')
        BookmarkManager.add_bookmark('Java Guide', 'https://java.com')
        results = BookmarkManager.search('Python')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], 'Python Guide')

    def test_get_by_folder(self):
        fid = self._create_folder('Dev')
        BookmarkManager.add_bookmark('Dev1', 'https://dev1.com', folder_id=fid)
        BookmarkManager.add_bookmark('NoFolder', 'https://nofolder.com')
        results = BookmarkManager.get_by_folder(fid)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], 'Dev1')

    def test_get_all(self):
        BookmarkManager.add_bookmark('A', 'https://a.com')
        BookmarkManager.add_bookmark('B', 'https://b.com')
        results = BookmarkManager.get_all()
        self.assertEqual(len(results), 2)

    def test_get_by_id(self):
        bid = BookmarkManager.add_bookmark('Test', 'https://test.com')
        bm = BookmarkManager.get_by_id(bid)
        self.assertIsNotNone(bm)
        self.assertEqual(bm['title'], 'Test')

    def test_get_by_id_nonexistent(self):
        self.assertIsNone(BookmarkManager.get_by_id(99999))

    def test_find_by_url(self):
        BookmarkManager.add_bookmark('Test', 'https://unique.com')
        bm = BookmarkManager.find_by_url('https://unique.com')
        self.assertIsNotNone(bm)
        self.assertEqual(bm['title'], 'Test')

    def test_find_by_url_nonexistent(self):
        self.assertIsNone(BookmarkManager.find_by_url('https://no.com'))

    def test_open_in_browser(self):
        bid = BookmarkManager.add_bookmark('OpenTest', 'https://open.com')
        BookmarkManager.open_in_browser(bid)
        self.assertEqual(len(self._opened_urls), 1)
        self.assertEqual(self._opened_urls[0]['url'], 'https://open.com')

    def test_open_in_browser_with_custom_browser(self):
        bid = BookmarkManager.add_bookmark('OpenTest', 'https://open.com', default_browser='C:\\chrome.exe')
        BookmarkManager.open_in_browser(bid, browser='C:\\firefox.exe')
        self.assertEqual(len(self._opened_urls), 1)
        self.assertEqual(self._opened_urls[0]['browser_path'], 'C:\\firefox.exe')

    def test_open_in_browser_records_history(self):
        from data.history_repo import HistoryRepo
        bid = BookmarkManager.add_bookmark('HistoryTest', 'https://history.com')
        BookmarkManager.open_in_browser(bid)
        records = HistoryRepo.get_by_bookmark(bid)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['opened_via'], 'manual')

    def test_open_in_browser_nonexistent_bookmark(self):
        BookmarkManager.open_in_browser(99999)
        self.assertEqual(len(self._opened_urls), 0)