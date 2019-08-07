from olive.exc import SaveError
from olive.store.cache_wrapper import CacheWrapper

from mango.core.models.survey import SurveySchema


class SurveyStore:
    def __init__(self, db, app):
        self.app = app
        self.db = db
        self.survey_schema = SurveySchema()
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
