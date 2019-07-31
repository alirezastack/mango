from mango.core.models.question import QuestionSchema
from olive.store.cache_wrapper import CacheWrapper
from olive.exc import SaveError, CacheNotFound
from olive.store.toolbox import to_object_id


class QuestionStore:
    def __init__(self, db, app):
        self.app = app
        self.db = db
        self.question_schema = QuestionSchema()
        self.cache_key = 'MANGO:QUESTION:{}'
        self.cache_wrapper = CacheWrapper(self.app, self.cache_key)

    def save(self, data):
        # raise validation error on invalid data
        self.question_schema.load(data)
        clean_data = self.question_schema.dump(data)
        if not clean_data:
            self.app.log.error('empty question payload cannot be saved.')
            raise SaveError

        self.app.log.debug('saving clean question:\n{}'.format(clean_data))
        question_id = self.db.save(clean_data)
        clean_data['_id'] = str(question_id)
        self.cache_wrapper.write_cache(question_id, clean_data)
        return str(question_id)

    def get_question_by_id(self, question_id):
        question_id = to_object_id(question_id)

        try:
            question_doc = self.cache_wrapper.get_cache(question_id)
        except CacheNotFound:
            self.app.log.debug('reading directly from database')
            question_doc = self.db.find_one({'_id': question_id}, {'created_at': 0})
            question_doc['_id'] = str(question_doc['_id'])
            self.cache_wrapper.write_cache(question_id, question_doc)

        clean_data = self.question_schema.load(question_doc)
        return clean_data
