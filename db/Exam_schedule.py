
class ExamSchedule:
    def __init__(self):
        self.id = None
        self.room = None
        self.exam_date = None
        self.exam_time = None

    def to_dict(self):
        return self.__dict__