import json
from tests.data.base import BaseDataTest
from data.schedule_repo import ScheduleRepo
from data.bookmark_repo import BookmarkRepo


class TestScheduleRepo(BaseDataTest):
    def test_create_returns_positive_id(self):
        sid = ScheduleRepo.create('Morning', 9, 0, 'daily')
        self.assertGreater(sid, 0)

    def test_create_with_repeat_days(self):
        sid = ScheduleRepo.create('Custom', 10, 30, 'custom', repeat_days='[1,3,5]')
        result = ScheduleRepo.get_by_id(sid)
        self.assertEqual(result['repeat_days'], '[1,3,5]')
        self.assertEqual(result['repeat_type'], 'custom')

    def test_get_by_id_returns_created(self):
        sid = ScheduleRepo.create('Test', 12, 0, 'once')
        result = ScheduleRepo.get_by_id(sid)
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], 'Test')
        self.assertEqual(result['hour'], 12)
        self.assertEqual(result['minute'], 0)
        self.assertEqual(result['repeat_type'], 'once')

    def test_get_by_id_nonexistent_returns_none(self):
        result = ScheduleRepo.get_by_id(99999)
        self.assertIsNone(result)

    def test_get_all_returns_all(self):
        ScheduleRepo.create('A', 8, 0, 'daily')
        ScheduleRepo.create('B', 12, 0, 'daily')
        ScheduleRepo.create('C', 18, 0, 'daily')
        results = ScheduleRepo.get_all()
        self.assertEqual(len(results), 3)

    def test_get_active_only_returns_active(self):
        sid1 = ScheduleRepo.create('Active', 9, 0, 'daily')
        sid2 = ScheduleRepo.create('Inactive', 10, 0, 'daily')
        ScheduleRepo.update(sid2, is_active=0)
        results = ScheduleRepo.get_active()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], sid1)

    def test_update_modifies_fields(self):
        sid = ScheduleRepo.create('Old', 8, 0, 'once')
        ScheduleRepo.update(sid, name='New', hour=14, minute=30, repeat_type='weekdays')
        result = ScheduleRepo.get_by_id(sid)
        self.assertEqual(result['name'], 'New')
        self.assertEqual(result['hour'], 14)
        self.assertEqual(result['minute'], 30)
        self.assertEqual(result['repeat_type'], 'weekdays')

    def test_delete_removes_schedule(self):
        sid = ScheduleRepo.create('To Delete', 9, 0, 'daily')
        ScheduleRepo.delete(sid)
        result = ScheduleRepo.get_by_id(sid)
        self.assertIsNone(result)

    def test_add_and_get_bookmarks(self):
        sid = ScheduleRepo.create('With Bookmarks', 9, 0, 'daily')
        bid1 = BookmarkRepo.create('BM1', 'https://1.com')
        bid2 = BookmarkRepo.create('BM2', 'https://2.com')
        bid3 = BookmarkRepo.create('BM3', 'https://3.com')
        ScheduleRepo.add_bookmark(sid, bid1, sort_order=0)
        ScheduleRepo.add_bookmark(sid, bid2, sort_order=1)
        ScheduleRepo.add_bookmark(sid, bid3, sort_order=2)
        bookmarks = ScheduleRepo.get_bookmarks(sid)
        self.assertEqual(len(bookmarks), 3)
        self.assertEqual(bookmarks[0]['id'], bid1)
        self.assertEqual(bookmarks[1]['id'], bid2)
        self.assertEqual(bookmarks[2]['id'], bid3)

    def test_add_bookmark_duplicate_ignored(self):
        sid = ScheduleRepo.create('Dup Test', 9, 0, 'daily')
        bid = BookmarkRepo.create('Unique', 'https://unique.com')
        ScheduleRepo.add_bookmark(sid, bid)
        ScheduleRepo.add_bookmark(sid, bid)
        bookmarks = ScheduleRepo.get_bookmarks(sid)
        self.assertEqual(len(bookmarks), 1)

    def test_remove_bookmark(self):
        sid = ScheduleRepo.create('Remove Test', 9, 0, 'daily')
        bid1 = BookmarkRepo.create('Keep', 'https://keep.com')
        bid2 = BookmarkRepo.create('Remove', 'https://remove.com')
        ScheduleRepo.add_bookmark(sid, bid1)
        ScheduleRepo.add_bookmark(sid, bid2)
        ScheduleRepo.remove_bookmark(sid, bid2)
        bookmarks = ScheduleRepo.get_bookmarks(sid)
        self.assertEqual(len(bookmarks), 1)
        self.assertEqual(bookmarks[0]['id'], bid1)

    def test_schedule_crud_flow(self):
        sid = ScheduleRepo.create('Flow Test', 10, 15, 'weekdays', '[1,2,3,4,5]')
        result = ScheduleRepo.get_by_id(sid)
        self.assertEqual(result['name'], 'Flow Test')
        ScheduleRepo.update(sid, name='Updated Flow', is_active=0)
        result = ScheduleRepo.get_by_id(sid)
        self.assertEqual(result['name'], 'Updated Flow')
        self.assertEqual(result['is_active'], 0)
        ScheduleRepo.delete(sid)
        self.assertIsNone(ScheduleRepo.get_by_id(sid))