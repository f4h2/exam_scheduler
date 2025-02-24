import json
class Room:
    def __init__(self):
        self.id = None
        self.name_room = None
        self.camera_links = []

    def to_dict(self):
        return {
            "id": self.id,
            "name_room": self.name_room,
            "camera_links": json.loads(self.camera_links) if isinstance(self.camera_links, str) else self.camera_links
        }