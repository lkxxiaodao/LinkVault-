from tests.core.base import BaseCoreTest
from core.folder_manager import FolderManager
from data.folder_repo import FolderRepo


class TestFolderManager(BaseCoreTest):
    def test_get_all(self):
        FolderManager.create_folder('A')
        FolderManager.create_folder('B')
        results = FolderManager.get_all()
        self.assertEqual(len(results), 2)

    def test_get_roots(self):
        FolderManager.create_folder('Root1')
        FolderManager.create_folder('Root2')
        roots = FolderManager.get_roots()
        self.assertEqual(len(roots), 2)

    def test_get_children(self):
        parent_id = FolderManager.create_folder('Parent')
        FolderManager.create_folder('Child1', parent_id=parent_id)
        FolderManager.create_folder('Child2', parent_id=parent_id)
        children = FolderManager.get_children(parent_id)
        self.assertEqual(len(children), 2)

    def test_get_by_id(self):
        fid = FolderManager.create_folder('Test')
        folder = FolderManager.get_by_id(fid)
        self.assertIsNotNone(folder)
        self.assertEqual(folder['name'], 'Test')

    def test_get_by_id_nonexistent(self):
        self.assertIsNone(FolderManager.get_by_id(99999))

    def test_create_folder(self):
        fid = FolderManager.create_folder('New Folder')
        self.assertGreater(fid, 0)
        folder = FolderRepo.get_by_id(fid)
        self.assertEqual(folder['name'], 'New Folder')

    def test_create_folder_with_parent(self):
        parent_id = FolderManager.create_folder('Parent')
        child_id = FolderManager.create_folder('Child', parent_id=parent_id)
        child = FolderRepo.get_by_id(child_id)
        self.assertEqual(child['parent_id'], parent_id)

    def test_update_folder(self):
        fid = FolderManager.create_folder('Old')
        FolderManager.update_folder(fid, name='New')
        folder = FolderRepo.get_by_id(fid)
        self.assertEqual(folder['name'], 'New')

    def test_delete_folder(self):
        fid = FolderManager.create_folder('Delete Me')
        FolderManager.delete_folder(fid)
        self.assertIsNone(FolderRepo.get_by_id(fid))

    def test_get_folder_tree_flat(self):
        FolderManager.create_folder('A')
        FolderManager.create_folder('B')
        tree = FolderManager.get_folder_tree()
        self.assertEqual(len(tree), 2)
        self.assertEqual(tree[0]['name'], 'A')
        self.assertEqual(tree[1]['name'], 'B')
        for node in tree:
            self.assertEqual(node['children'], [])

    def test_get_folder_tree_nested(self):
        parent_id = FolderManager.create_folder('Parent')
        child1_id = FolderManager.create_folder('Child1', parent_id=parent_id)
        child2_id = FolderManager.create_folder('Child2', parent_id=parent_id)
        FolderManager.create_folder('Grandchild', parent_id=child1_id)

        tree = FolderManager.get_folder_tree()
        self.assertEqual(len(tree), 1)
        self.assertEqual(tree[0]['name'], 'Parent')
        self.assertEqual(len(tree[0]['children']), 2)
        child_names = [c['name'] for c in tree[0]['children']]
        self.assertIn('Child1', child_names)
        self.assertIn('Child2', child_names)

        child1 = [c for c in tree[0]['children'] if c['name'] == 'Child1'][0]
        self.assertEqual(len(child1['children']), 1)
        self.assertEqual(child1['children'][0]['name'], 'Grandchild')

    def test_get_folder_tree_has_depth(self):
        parent_id = FolderManager.create_folder('Parent')
        FolderManager.create_folder('Child', parent_id=parent_id)
        tree = FolderManager.get_folder_tree()
        self.assertEqual(tree[0]['depth'], 0)
        self.assertEqual(tree[0]['children'][0]['depth'], 1)