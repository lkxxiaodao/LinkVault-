from data.folder_repo import FolderRepo


class FolderManager:
    @staticmethod
    def get_all():
        return FolderRepo.get_all()

    @staticmethod
    def get_roots():
        return FolderRepo.get_by_parent(None)

    @staticmethod
    def get_children(parent_id):
        return FolderRepo.get_by_parent(parent_id)

    @staticmethod
    def get_by_id(folder_id):
        return FolderRepo.get_by_id(folder_id)

    @staticmethod
    def create_folder(name, parent_id=None):
        return FolderRepo.create(name, parent_id)

    @staticmethod
    def update_folder(folder_id, **kwargs):
        FolderRepo.update(folder_id, **kwargs)

    @staticmethod
    def delete_folder(folder_id):
        FolderRepo.delete(folder_id)