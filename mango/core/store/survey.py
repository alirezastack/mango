from olive.exc import SaveError, CacheNotFound, DocumentNotFound
from olive.store.cache_wrapper import CacheWrapper
from mango.core.models.survey import SurveySchema
from olive.exc import InvalidFilter
from pprint import pformat
import pymongo


class SurveyStore:
    def __init__(self, db, app):
        self.app = app
        self.db = db
        self.survey_schema = SurveySchema(exclude_id=True)
        self.cache_key = 'MANGO:SURVEY:{}'
        self.cache_wrapper = CacheWrapper(self.app, self.cache_key)

    def save(self, data):
        # raise validation error on invalid data
        self.survey_schema.load(data)
        clean_data = self.survey_schema.dump(data)
        if not clean_data:
            self.app.log.error('empty survey payload cannot be saved.')
            raise SaveError

        self.app.log.debug('saving clean survey:\n{}'.format(clean_data))
        survey_id = self.db.save(clean_data)
        clean_data['_id'] = str(survey_id)
        return str(survey_id)

    def get_by_reservation_id(self, reservation_id):
        try:
            survey_doc = self.cache_wrapper.get_cache('BY_RESERVATION:{}'.format(reservation_id))
        except CacheNotFound:
            self.app.log.debug('reading directly from database')
            survey_doc = self.db.find_one({'reservation_id': reservation_id}, {'created_at': 0, 'updated_at': 0})
            if not survey_doc:
                raise DocumentNotFound("Document with reservation_id {} not found!".format(reservation_id))

            survey_doc['_id'] = str(survey_doc['_id'])
            self.cache_wrapper.write_cache('BY_RESERVATION:{}'.format(reservation_id), survey_doc)

        clean_data = self.survey_schema.load(survey_doc)
        return clean_data

    def get_surveys(self, skip, limit, sort_key='+total_rating'):
        skip, limit = skip or 0, min(limit or 50, 200)
        self.app.log.debug('reading surveys from database by below filters...')
        self.app.log.info('skip={} limit={} sort_key={}'.format(skip, limit, sort_key))

        sort_direction = {
            '-': pymongo.DESCENDING,
            '+': pymongo.ASCENDING
        }
        if sort_key[:1] not in sort_direction.keys():
            raise InvalidFilter('invalid sort_key given: {}, it should start with - or +'.format(sort_key))

        survey_docs = self.db.find(filter={},
                                   projection={'created_at': 0, 'updated_at': 0},
                                   skip=skip,
                                   limit=limit,
                                   sort=[(sort_key[1:], sort_direction[sort_key[:1]])])
        clean_data = self.survey_schema.load(survey_docs, many=True)
        self.app.log.info('surveys result: \n{}'.format(pformat(clean_data)))
        return survey_docs.count(), clean_data
