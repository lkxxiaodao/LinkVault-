from tests.data.base import BaseDataTest
from data.history_repo import HistoryRepo
from data.bookmark_repo import BookmarkRepo


class TestHistoryRepo(BaseDataTest):
    def test_record_creates_history_entry(self):
        bid = BookmarkRepo.create('Test', 'https://example.com')
        HistoryRepo.record(bid, opened_via='manual')
        results = HistoryRepo.get_recent(days=30)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['bookmark_id'], bid)
        self.assertEqual(results[0]['opened_via'], 'manual')

    def test_record_default_via_is_manual(self):
        bid = BookmarkRepo.create('Default Via', 'https://default.com')
        HistoryRepo.record(bid)
        results = HistoryRepo.get_recent(days=30)
        self.assertEqual(results[0]['opened_via'], 'manual')

    def test_record_multiple_entries(self):
        bid = BookmarkRepo.create('Multi', 'https://multi.com')
        for _ in range(5):
            HistoryRepo.record(bid)
        results = HistoryRepo.get_recent(days=30)
        self.assertEqual(len(results), 5)

    def test_get_by_bookmark_filters_correctly(self):
        bid1 = BookmarkRepo.create('BM1', 'https://1.com')
        bid2 = BookmarkRepo.create('BM2', 'https://2.com')
        HistoryRepo.record(bid1)
        HistoryRepo.record(bid1)
        HistoryRepo.record(bid2)
        results = HistoryRepo.get_by_bookmark(bid1, days=30)
        self.assertEqual(len(results), 2)
        for r in results:
            self.assertEqual(r['bookmark_id'], bid1)

    def test_get_by_bookmark_respects_days(self):
        bid = BookmarkRepo.create('Days Test', 'https://days.com')
        HistoryRepo.record(bid)
        results = HistoryRepo.get_by_bookmark(bid, days=1)
        self.assertEqual(len(results), 1)

    def test_get_recent_respects_days(self):
        bid = BookmarkRepo.create('Recent Test', 'https://recent.com')
        HistoryRepo.record(bid)
        results = HistoryRepo.get_recent(days=1)
        self.assertEqual(len(results), 1)

    def test_get_recent_ordered_desc(self):
        bid = BookmarkRepo.create('Order Test', 'https://order.com')
        HistoryRepo.record(bid, opened_via='schedule')
        HistoryRepo.record(bid, opened_via='random')
        HistoryRepo.record(bid, opened_via='manual')
        results = HistoryRepo.get_recent(days=30)
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]['opened_via'], 'manual')
        self.assertEqual(results[1]['opened_via'], 'random')
        self.assertEqual(results[2]['opened_via'], 'schedule')

    def test_history_crud_flow(self):
        bid = BookmarkRepo.create('CRUD History', 'https://crud.com')
        HistoryRepo.record(bid, opened_via='manual')
        results = HistoryRepo.get_recent(days=30)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['bookmark_id'], bid)
        self.assertEqual(results[0]['opened_via'], 'manual')