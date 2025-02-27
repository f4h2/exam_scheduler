import json
class RoomPy:
    def __init__(self):
        self.uuidLocation = None
        self.name = None
        self.description = None
        self.uuidOrganization = None
    def to_dict(self):
        return {
            "id": self.uuidLocation,
            "name": self.name,
            "description": self.description,
            "uuidOrganization":self.uuidOrganization
        }