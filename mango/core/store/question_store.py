from mango.core.models.question import QuestionSchema
from olive.exc import SaveError
from bson import ObjectId


class QuestionStore:
    def __init__(self, db, app):
        self.app = app
        self.db = db
        self.question_schema = QuestionSchema()

    def save(self, data):
        # raise validation error on invalid data
        self.question_schema.load(data)
        clean_data = self.question_schema.dump(data)
        if not clean_data:
            self.app.log.error('empty question payload cannot be saved.')
            raise SaveError

        self.app.log.debug('saving clean question:\n{}'.format(clean_data))
        question_id = self.db.save(clean_data)
        return str(question_id)

    def get_question_by_id(self, question_id):
        self.app.log.debug('getting question by ID: {}'.format(question_id))
        question_doc = self.db.find_one({'_id': ObjectId(question_id)}, {'created_at': 0})
        clean_data = self.question_schema.load(question_doc)
        self.app.log.info('fetched question:\r\n{}'.format(clean_data))
        return clean_data
