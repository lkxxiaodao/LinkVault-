from tests.data.base import BaseDataTest
from data.bookmark_repo import BookmarkRepo


class TestBookmarkRepo(BaseDataTest):
    def test_create_returns_positive_id(self):
        bid = BookmarkRepo.create('Test', 'https://example.com')
        self.assertGreater(bid, 0)

    def test_get_by_id_returns_created(self):
        bid = BookmarkRepo.create('Test Bookmark', 'https://example.com')
        result = BookmarkRepo.get_by_id(bid)
        self.assertIsNotNone(result)
        self.assertEqual(result['title'], 'Test Bookmark')
        self.assertEqual(result['url'], 'https://example.com')

    def test_get_by_id_nonexistent_returns_none(self):
        result = BookmarkRepo.get_by_id(99999)
        self.assertIsNone(result)

    def test_get_all_returns_all_bookmarks(self):
        BookmarkRepo.create('A', 'https://a.com')
        BookmarkRepo.create('B', 'https://b.com')
        BookmarkRepo.create('C', 'https://c.com')
        results = BookmarkRepo.get_all()
        self.assertEqual(len(results), 3)

    def test_get_all_ordered_by_title(self):
        BookmarkRepo.create('Zebra', 'https://z.com')
        BookmarkRepo.create('Apple', 'https://a.com')
        BookmarkRepo.create('Mango', 'https://m.com')
        results = BookmarkRepo.get_all()
        titles = [r['title'] for r in results]
        self.assertEqual(titles, ['Apple', 'Mango', 'Zebra'])

    def test_get_by_folder_filters_correctly(self):
        fid = self._create_folder('Work')
        BookmarkRepo.create('Work Link', 'https://work.com', folder_id=fid)
        BookmarkRepo.create('No Folder Link', 'https://nofolder.com')
        results = BookmarkRepo.get_by_folder(fid)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], 'Work Link')

    def test_search_by_title(self):
        BookmarkRepo.create('Python Guide', 'https://py.com')
        BookmarkRepo.create('Java Guide', 'https://java.com')
        BookmarkRepo.create('Python Advanced', 'https://pyadv.com')
        results = BookmarkRepo.search('Python')
        self.assertEqual(len(results), 2)

    def test_search_by_url(self):
        BookmarkRepo.create('Site A', 'https://github.com/repo1')
        BookmarkRepo.create('Site B', 'https://gitlab.com/repo2')
        BookmarkRepo.create('Site C', 'https://github.com/repo3')
        results = BookmarkRepo.search('github')
        self.assertEqual(len(results), 2)

    def test_search_case_insensitive(self):
        BookmarkRepo.create('PYTHON ROCKS', 'https://py.com')
        results = BookmarkRepo.search('python')
        self.assertEqual(len(results), 1)

    def test_find_by_url_returns_existing(self):
        BookmarkRepo.create('Test', 'https://unique.example.com')
        result = BookmarkRepo.find_by_url('https://unique.example.com')
        self.assertIsNotNone(result)
        self.assertEqual(result['title'], 'Test')

    def test_find_by_url_returns_none_for_new(self):
        result = BookmarkRepo.find_by_url('https://notexist.example.com')
        self.assertIsNone(result)

    def test_update_modifies_fields(self):
        bid = BookmarkRepo.create('Old Title', 'https://old.com')
        BookmarkRepo.update(bid, title='New Title', url='https://new.com')
        result = BookmarkRepo.get_by_id(bid)
        self.assertEqual(result['title'], 'New Title')
        self.assertEqual(result['url'], 'https://new.com')

    def test_update_ignores_invalid_fields(self):
        bid = BookmarkRepo.create('Safe', 'https://safe.com')
        BookmarkRepo.update(bid, invalid_field='hacked')
        result = BookmarkRepo.get_by_id(bid)
        self.assertNotIn('invalid_field', result)

    def test_delete_removes_bookmark(self):
        bid = BookmarkRepo.create('To Delete', 'https://delete.com')
        BookmarkRepo.delete(bid)
        result = BookmarkRepo.get_by_id(bid)
        self.assertIsNone(result)

    def test_move_to_folder_changes_folder(self):
        fid1 = self._create_folder('Folder 1')
        fid2 = self._create_folder('Folder 2')
        bid = BookmarkRepo.create('Movable', 'https://move.com', folder_id=fid1)
        BookmarkRepo.move_to_folder(bid, fid2)
        result = BookmarkRepo.get_by_id(bid)
        self.assertEqual(result['folder_id'], fid2)

    def test_move_to_folder_none(self):
        fid = self._create_folder('Temp')
        bid = BookmarkRepo.create('To Unfolder', 'https://unfolder.com', folder_id=fid)
        BookmarkRepo.move_to_folder(bid, None)
        result = BookmarkRepo.get_by_id(bid)
        self.assertIsNone(result['folder_id'])

    def _create_folder(self, name, parent_id=None):
        from data.folder_repo import FolderRepo
        return FolderRepo.create(name, parent_id)