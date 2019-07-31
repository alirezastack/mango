from olive.consts import DELETED_STATUS, ACTIVE_STATUS, INACTIVE_STATUS
from olive.exc import SaveError, CacheNotFound, DocumentNotFound
from mango.core.models.question import QuestionSchema
from olive.store.cache_wrapper import CacheWrapper
from olive.store.toolbox import to_object_id
from olive.exc import InvalidObjectId
from bson import ObjectId
import traceback
import bson


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

    def get_question_by_id(self, question_id, status='active'):
        try:
            question_id = ObjectId(question_id)
        except bson.errors.InvalidId:
            self.app.log.error(traceback.format_exc())
            raise InvalidObjectId

        try:
            _key = '{}:{}'.format(question_id, status.upper())
            question_doc = self.cache_wrapper.get_cache(_key)
        except CacheNotFound:
            self.app.log.debug('reading directly from database')
            question_doc = self.db.find_one({'_id': question_id, 'status': status.lower()}, {'created_at': 0})
            if not question_doc:
                raise DocumentNotFound("Document {} with status {} not found!".format(question_id, status))

            question_doc['_id'] = str(question_doc['_id'])
            _key = '{}:{}'.format(question_id, question_doc['status'].upper())
            self.cache_wrapper.write_cache(
                key=_key,
                value=question_doc)

        clean_data = self.question_schema.load(question_doc)
        return clean_data

    def delete(self, question_id):
        question_id = to_object_id(question_id)
        self.cache_wrapper.delete('{}:{}'.format(question_id, ACTIVE_STATUS.upper()))
        self.cache_wrapper.delete('{}:{}'.format(question_id, INACTIVE_STATUS.upper()))
        update_result = self.db.update({'_id': question_id}, {'$set': {'status': DELETED_STATUS}})
        self.app.log.info('question {} deletion result: {}'.format(question_id, update_result))

        # https://docs.mongodb.com/manual/reference/command/update/#update.nModified
        return update_result.get('nModified', 0)
