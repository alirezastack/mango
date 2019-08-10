from mango.core.models.question import QuestionSchema
from olive.consts import DELETED_STATUS, ACTIVE_STATUS, INACTIVE_STATUS
from olive.exc import SaveError, CacheNotFound, DocumentNotFound
from olive.store.cache_wrapper import CacheWrapper
from olive.store.toolbox import to_object_id


class QuestionStore:
    def __init__(self, db, app):
        self.app = app
        self.db = db
        self.question_schema = QuestionSchema(exclude_none_id=True)
        self.cache_key = 'MANGO:QUESTION:{}'
        self.cache_questions_key = 'ALL'
        self.cache_wrapper = CacheWrapper(self.app, self.cache_key)

    def save(self, data):
        # raise validation error on invalid data
        self.question_schema.load(data)
        clean_data = self.question_schema.dump(data)
        if not clean_data:
            self.app.log.error('empty question payload cannot be saved.')
            raise SaveError

        self.cache_wrapper.delete('ALL')

        self.app.log.debug('saving clean question:\n{}'.format(clean_data))
        question_id = self.db.save(clean_data)
        clean_data['_id'] = str(question_id)
        self.cache_wrapper.delete(self.cache_questions_key)
        return str(question_id)

    def update(self, question_id, question):
        question_id = to_object_id(question_id)

        if question['status'] == DELETED_STATUS:
            raise SaveError('question {} with status of {} cannot be saved via update() method'
                            .format(question_id, DELETED_STATUS))

        # raise validation error on invalid data
        self.question_schema.load(question)
        clean_data = self.question_schema.dump(question)
        if not clean_data:
            raise SaveError('empty question payload cannot be saved.')

        self.app.log.debug('updating question {}...'.format(question_id))
        update_res = self.db.update_one({'_id': question_id}, {'$set': question})
        modified_count = update_res.modified_count
        self.app.log.info('update question {}: matchedCount:{} modifiedCount:{}'.format(question_id,
                                                                                        update_res.matched_count,
                                                                                        modified_count))
        if modified_count:
            question['_id'] = str(question_id)
            self.cache_wrapper.write_cache(question_id, question)
            self.cache_wrapper.delete(self.cache_questions_key)

        return modified_count

    def get_question_by_id(self, question_id):
        question_id = to_object_id(question_id)

        try:
            question_doc = self.cache_wrapper.get_cache(question_id)
        except CacheNotFound:
            self.app.log.debug('reading directly from database')
            question_doc = self.db.find_one({'_id': question_id}, {'created_at': 0})
            if not question_doc:
                raise DocumentNotFound("Document {} not found!".format(question_id))

            question_doc['_id'] = str(question_doc['_id'])
            if question_doc['status'] != DELETED_STATUS:
                self.cache_wrapper.write_cache(question_id, question_doc)

        clean_data = self.question_schema.load(question_doc)
        return clean_data

    # TODO: zoodroom-backend compatibility
    def get_questions_by_filters(self, question_ids, include_in=None, status=None, project=None):
        all_fields = {'weight', 'status', 'order', 'include_in', 'title', 'category'}
        partial = None
        project = project if type(project) in [list, dict] else None
        if project:
            if type(project) == dict:
                partial = tuple(all_fields - set(project.keys()))
            elif type(project) == list:
                partial = tuple(all_fields - set(project))

        question_ids = [to_object_id(i) for i in question_ids]
        filter_args = {
            "_id": {
                "$in": question_ids
            }
        }

        if include_in:
            filter_args["include_in"] = include_in

        if status:
            filter_args['status'] = status

        questions = list(self.db.find(filter=filter_args, projection=project))
        return self.question_schema.load(questions, many=True, partial=partial)

    def delete(self, question_id):
        question_id = to_object_id(question_id)
        self.cache_wrapper.delete(question_id)
        self.cache_wrapper.delete('ALL')
        update_result = self.db.update({'_id': question_id}, {'$set': {'status': DELETED_STATUS}})
        modified_count = update_result['nModified']

        if modified_count:
            self.cache_wrapper.delete(self.cache_questions_key)

        self.app.log.info('question {} deletion result: {}'.format(question_id, update_result))

        # https://docs.mongodb.com/manual/reference/command/update/#update.nModified
        return update_result.get('nModified', 0)

    def get_questions(self):
        try:
            questions_docs = self.cache_wrapper.get_cache(self.cache_questions_key)
        except CacheNotFound:
            self.app.log.debug('reading questions directly from database')
            questions_cursor = self.db.find({'status': {'$in': [ACTIVE_STATUS, INACTIVE_STATUS]}}, {'created_at': 0})
            questions_docs = self.question_schema.load(questions_cursor, many=True)
            if not questions_docs:
                return questions_docs
            self.cache_wrapper.write_cache(self.cache_questions_key, questions_docs)

        return questions_docs
