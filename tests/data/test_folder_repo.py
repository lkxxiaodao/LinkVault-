from tests.data.base import BaseDataTest
from data.folder_repo import FolderRepo


class TestFolderRepo(BaseDataTest):
    def test_create_returns_positive_id(self):
        fid = FolderRepo.create('Root Folder')
        self.assertGreater(fid, 0)

    def test_get_by_id_returns_created(self):
        fid = FolderRepo.create('My Folder')
        result = FolderRepo.get_by_id(fid)
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], 'My Folder')

    def test_get_by_id_nonexistent_returns_none(self):
        result = FolderRepo.get_by_id(99999)
        self.assertIsNone(result)

    def test_get_all_returns_all_folders(self):
        FolderRepo.create('A')
        FolderRepo.create('B')
        FolderRepo.create('C')
        results = FolderRepo.get_all()
        self.assertEqual(len(results), 3)

    def test_get_by_parent_root(self):
        root1 = FolderRepo.create('Root 1')
        root2 = FolderRepo.create('Root 2')
        sub_fid = FolderRepo.create('Sub')
        FolderRepo.update(sub_fid, parent_id=root1)
        root_folders = FolderRepo.get_by_parent(None)
        self.assertEqual(len(root_folders), 2)

    def test_get_by_parent_specific(self):
        parent_id = FolderRepo.create('Parent')
        FolderRepo.create('Child 1', parent_id=parent_id)
        FolderRepo.create('Child 2', parent_id=parent_id)
        FolderRepo.create('Other Child', parent_id=None)
        children = FolderRepo.get_by_parent(parent_id)
        self.assertEqual(len(children), 2)

    def test_update_modifies_fields(self):
        fid = FolderRepo.create('Old Name')
        FolderRepo.update(fid, name='New Name', sort_order=5)
        result = FolderRepo.get_by_id(fid)
        self.assertEqual(result['name'], 'New Name')
        self.assertEqual(result['sort_order'], 5)

    def test_delete_removes_folder(self):
        fid = FolderRepo.create('To Delete')
        FolderRepo.delete(fid)
        result = FolderRepo.get_by_id(fid)
        self.assertIsNone(result)

    def test_get_children_recursive_single_level(self):
        fid = FolderRepo.create('Root')
        result = FolderRepo.get_children_recursive(fid)
        self.assertEqual(result, [fid])

    def test_get_children_recursive_three_levels(self):
        level1 = FolderRepo.create('Level 1')
        level2 = FolderRepo.create('Level 2', parent_id=level1)
        level3 = FolderRepo.create('Level 3', parent_id=level2)
        result = FolderRepo.get_children_recursive(level1)
        self.assertEqual(set(result), {level1, level2, level3})

    def test_get_children_recursive_multiple_branches(self):
        root = FolderRepo.create('Root')
        child_a = FolderRepo.create('Child A', parent_id=root)
        child_b = FolderRepo.create('Child B', parent_id=root)
        grand_a = FolderRepo.create('Grand A', parent_id=child_a)
        grand_b1 = FolderRepo.create('Grand B1', parent_id=child_b)
        grand_b2 = FolderRepo.create('Grand B2', parent_id=child_b)
        result = FolderRepo.get_children_recursive(root)
        self.assertEqual(set(result), {root, child_a, child_b, grand_a, grand_b1, grand_b2})