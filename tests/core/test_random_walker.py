from tests.core.base import BaseCoreTest
from core.random_walker import RandomWalker
from data.pool_repo import PoolRepo
from data.bookmark_repo import BookmarkRepo
from data.history_repo import HistoryRepo


class TestRandomWalker(BaseCoreTest):
    def test_create_pool(self):
        pid = RandomWalker.create_pool('My Pool')
        self.assertGreater(pid, 0)
        pool = PoolRepo.get_by_id(pid)
        self.assertEqual(pool['name'], 'My Pool')

    def test_delete_pool(self):
        pid = RandomWalker.create_pool('Delete Me')
        RandomWalker.delete_pool(pid)
        self.assertIsNone(PoolRepo.get_by_id(pid))

    def test_get_all_pools(self):
        RandomWalker.create_pool('A')
        RandomWalker.create_pool('B')
        pools = RandomWalker.get_all_pools()
        self.assertEqual(len(pools), 2)

    def test_set_active_pool(self):
        pid1 = RandomWalker.create_pool('Pool1')
        pid2 = RandomWalker.create_pool('Pool2')
        RandomWalker.set_active_pool(pid1)
        active = RandomWalker.get_active_pool()
        self.assertIsNotNone(active)
        self.assertEqual(active['id'], pid1)

        RandomWalker.set_active_pool(pid2)
        active = RandomWalker.get_active_pool()
        self.assertEqual(active['id'], pid2)

    def test_get_active_pool_none(self):
        active = RandomWalker.get_active_pool()
        self.assertIsNone(active)

    def test_add_to_pool(self):
        pid = RandomWalker.create_pool('Test Pool')
        bid = BookmarkRepo.create('Test BM', 'https://test.com')
        RandomWalker.add_to_pool(pid, bid)
        bookmarks = PoolRepo.get_bookmarks(pid)
        self.assertEqual(len(bookmarks), 1)
        self.assertEqual(bookmarks[0]['id'], bid)

    def test_remove_from_pool(self):
        pid = RandomWalker.create_pool('Test Pool')
        bid = BookmarkRepo.create('Test BM', 'https://test.com')
        RandomWalker.add_to_pool(pid, bid)
        RandomWalker.remove_from_pool(pid, bid)
        bookmarks = PoolRepo.get_bookmarks(pid)
        self.assertEqual(len(bookmarks), 0)

    def test_get_pool_bookmarks(self):
        pid = RandomWalker.create_pool('Test Pool')
        b1 = BookmarkRepo.create('B1', 'https://b1.com')
        b2 = BookmarkRepo.create('B2', 'https://b2.com')
        RandomWalker.add_to_pool(pid, b1)
        RandomWalker.add_to_pool(pid, b2)
        bookmarks = RandomWalker.get_pool_bookmarks(pid)
        self.assertEqual(len(bookmarks), 2)

    def test_walk_no_active_pool(self):
        result = RandomWalker.walk()
        self.assertIsNone(result)
        self.assertEqual(len(self._opened_urls), 0)

    def test_walk_empty_pool(self):
        pid = RandomWalker.create_pool('Empty Pool')
        RandomWalker.set_active_pool(pid)
        result = RandomWalker.walk()
        self.assertIsNone(result)
        self.assertEqual(len(self._opened_urls), 0)

    def test_walk_opens_random_bookmark(self):
        pid = RandomWalker.create_pool('Walk Pool')
        b1 = BookmarkRepo.create('B1', 'https://b1.com')
        b2 = BookmarkRepo.create('B2', 'https://b2.com')
        RandomWalker.add_to_pool(pid, b1)
        RandomWalker.add_to_pool(pid, b2)
        RandomWalker.set_active_pool(pid)

        result = RandomWalker.walk()
        self.assertIsNotNone(result)
        self.assertIn(result['url'], ['https://b1.com', 'https://b2.com'])
        self.assertEqual(len(self._opened_urls), 1)

    def test_walk_records_history(self):
        pid = RandomWalker.create_pool('History Pool')
        bid = BookmarkRepo.create('History BM', 'https://history.com')
        RandomWalker.add_to_pool(pid, bid)
        RandomWalker.set_active_pool(pid)

        RandomWalker.walk()
        records = HistoryRepo.get_by_bookmark(bid)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['opened_via'], 'random')

    def test_walk_uses_default_browser(self):
        pid = RandomWalker.create_pool('Browser Pool')
        bid = BookmarkRepo.create('Browser BM', 'https://browser.com', default_browser='C:\\custom.exe')
        RandomWalker.add_to_pool(pid, bid)
        RandomWalker.set_active_pool(pid)

        RandomWalker.walk()
        self.assertEqual(len(self._opened_urls), 1)
        self.assertEqual(self._opened_urls[0]['browser_path'], 'C:\\custom.exe')