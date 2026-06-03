from tests.data.base import BaseDataTest
from data.pool_repo import PoolRepo
from data.bookmark_repo import BookmarkRepo


class TestPoolRepo(BaseDataTest):
    def test_create_returns_positive_id(self):
        pid = PoolRepo.create('My Pool')
        self.assertGreater(pid, 0)

    def test_get_by_id_returns_created(self):
        pid = PoolRepo.create('Test Pool')
        result = PoolRepo.get_by_id(pid)
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], 'Test Pool')
        self.assertEqual(result['is_active'], 0)

    def test_get_by_id_nonexistent_returns_none(self):
        result = PoolRepo.get_by_id(99999)
        self.assertIsNone(result)

    def test_get_all_returns_all(self):
        PoolRepo.create('Pool A')
        PoolRepo.create('Pool B')
        PoolRepo.create('Pool C')
        results = PoolRepo.get_all()
        self.assertEqual(len(results), 3)

    def test_get_active_returns_none_when_no_active(self):
        PoolRepo.create('Pool 1')
        PoolRepo.create('Pool 2')
        result = PoolRepo.get_active()
        self.assertIsNone(result)

    def test_set_active_makes_only_one_active(self):
        pid1 = PoolRepo.create('Pool 1')
        pid2 = PoolRepo.create('Pool 2')
        PoolRepo.set_active(pid1)
        active = PoolRepo.get_active()
        self.assertIsNotNone(active)
        self.assertEqual(active['id'], pid1)
        PoolRepo.set_active(pid2)
        active = PoolRepo.get_active()
        self.assertEqual(active['id'], pid2)
        all_pools = PoolRepo.get_all()
        active_count = sum(1 for p in all_pools if p['is_active'] == 1)
        self.assertEqual(active_count, 1)

    def test_set_active_none_deactivates_all(self):
        pid = PoolRepo.create('Pool')
        PoolRepo.set_active(pid)
        PoolRepo.set_active(None)
        result = PoolRepo.get_active()
        self.assertIsNone(result)

    def test_update_modifies_fields(self):
        pid = PoolRepo.create('Old Name')
        PoolRepo.update(pid, name='New Name')
        result = PoolRepo.get_by_id(pid)
        self.assertEqual(result['name'], 'New Name')

    def test_delete_removes_pool(self):
        pid = PoolRepo.create('To Delete')
        PoolRepo.delete(pid)
        result = PoolRepo.get_by_id(pid)
        self.assertIsNone(result)

    def test_add_and_get_bookmarks(self):
        pid = PoolRepo.create('Bookmark Pool')
        bid1 = BookmarkRepo.create('BM1', 'https://1.com')
        bid2 = BookmarkRepo.create('BM2', 'https://2.com')
        bid3 = BookmarkRepo.create('BM3', 'https://3.com')
        PoolRepo.add_bookmark(pid, bid1)
        PoolRepo.add_bookmark(pid, bid2)
        PoolRepo.add_bookmark(pid, bid3)
        bookmarks = PoolRepo.get_bookmarks(pid)
        self.assertEqual(len(bookmarks), 3)

    def test_add_bookmark_duplicate_ignored(self):
        pid = PoolRepo.create('Dup Pool')
        bid = BookmarkRepo.create('Unique', 'https://unique.com')
        PoolRepo.add_bookmark(pid, bid)
        PoolRepo.add_bookmark(pid, bid)
        bookmarks = PoolRepo.get_bookmarks(pid)
        self.assertEqual(len(bookmarks), 1)

    def test_remove_bookmark(self):
        pid = PoolRepo.create('Remove Pool')
        bid1 = BookmarkRepo.create('Keep', 'https://keep.com')
        bid2 = BookmarkRepo.create('Remove', 'https://remove.com')
        PoolRepo.add_bookmark(pid, bid1)
        PoolRepo.add_bookmark(pid, bid2)
        PoolRepo.remove_bookmark(pid, bid2)
        bookmarks = PoolRepo.get_bookmarks(pid)
        self.assertEqual(len(bookmarks), 1)
        self.assertEqual(bookmarks[0]['id'], bid1)

    def test_pool_crud_flow(self):
        pid = PoolRepo.create('CRUD Pool')
        result = PoolRepo.get_by_id(pid)
        self.assertEqual(result['name'], 'CRUD Pool')
        PoolRepo.update(pid, name='Updated Pool')
        result = PoolRepo.get_by_id(pid)
        self.assertEqual(result['name'], 'Updated Pool')
        PoolRepo.delete(pid)
        self.assertIsNone(PoolRepo.get_by_id(pid))