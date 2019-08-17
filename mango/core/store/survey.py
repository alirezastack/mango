from olive.exc import SaveError, CacheNotFound, DocumentNotFound
from olive.store.cache_wrapper import CacheWrapper
from mango.core.models.survey import SurveySchema
from olive.toolbox import generate_sha256
from olive.exc import InvalidFilter
from pprint import pformat
import pymongo


class SurveyStore:
    def __init__(self, db, app):
        self.app = app
        self.db = db
        self.survey_schema = SurveySchema(exclude_none_id=True)
        self.cache_key = 'MANGO:SURVEY:{}'
        self.get_surveys_cache_key = 'GET_SURVEYS:{}'
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

        # purge all survey caches with filters
        self.cache_wrapper.delete_by_pattern('{}*'.format(self.cache_key.format(self.get_surveys_cache_key.format(''))))

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

    def stream_surveys(self):
        surveys = self.db.find({})
        for survey in surveys:
            self.app.log.debug('yielding survey document: {}'.format(survey['_id']))
            yield self.survey_schema.load(survey)

    def get_surveys(self, skip, limit, sort_key='+total_rating'):
        skip, limit = skip or 0, min(limit or 50, 200)

        cache_key = generate_sha256('skip:{}limit:{}{}'.format(skip, limit, sort_key))

        try:
            survey_docs = self.cache_wrapper.get_cache(self.get_surveys_cache_key
                                                       .format(cache_key))
            total_count = self.cache_wrapper.get_cache(self.get_surveys_cache_key
                                                       .format('{}:COUNT'.format(cache_key)))['total_count']
        except CacheNotFound:
            self.app.log.debug('reading surveys directly from database by below filters...')
            self.app.log.info('skip={} limit={} sort_key={}'.format(skip, limit, sort_key))

            sort_direction = {
                '-': pymongo.DESCENDING,
                '+': pymongo.ASCENDING
            }
            if sort_key[:1] not in sort_direction.keys():
                raise InvalidFilter('invalid sort_key given: {}, it should start with - or +'.format(sort_key))

            survey_docs_cursor = self.db.find(filter={},
                                              projection={'created_at': 0, 'updated_at': 0},
                                              skip=skip,
                                              limit=limit,
                                              sort=[(sort_key[1:], sort_direction[sort_key[:1]])])

            total_count = survey_docs_cursor.count()

            survey_docs = self.survey_schema.load(survey_docs_cursor, many=True)
            if not survey_docs:
                return total_count, survey_docs

            self.cache_wrapper.write_cache(self.get_surveys_cache_key
                                           .format(cache_key), survey_docs)
            self.cache_wrapper.write_cache(key=self.get_surveys_cache_key.format('{}:COUNT'.format(cache_key)),
                                           value={'total_count': total_count})

        self.app.log.info('surveys result: \n{}'.format(pformat(survey_docs)))

        return total_count, survey_docs
