from olive.toolbox import MarshmallowDateTimeField
from marshmallow import Schema, fields, EXCLUDE
from olive.consts import UTC_DATE_FORMAT
import datetime


class SurveyQuestion(Schema):
    question_id = fields.Str(required=True,
                             error_messages={'required': {'message': 'question_id is required', 'code': 400}})
    rating = fields.Int(required=True,
                        error_messages={'required': {'message': 'question_id is required', 'code': 400}})


class SurveySchema(Schema):
    class Meta:
        # Tuple or list of fields to include in the serialized result
        fields = ("_id", "created_at", "updated_at", "user_id", "staff_id", "total_rating",
                  "reservation_id", "status", "questions", "content", "platform")
        # exclude unknown fields from database on .load() call
        unknown = EXCLUDE
        datetimeformat = UTC_DATE_FORMAT

    created_at = MarshmallowDateTimeField(dump_only=True,
                                          default=lambda: datetime.datetime.utcnow(),
                                          allow_none=False)
    updated_at = MarshmallowDateTimeField(dump_only=True,
                                          default=lambda: datetime.datetime.utcnow(),
                                          allow_none=False)
    user_id = fields.Str(required=True,
                         error_messages={'required': {'message': 'user_id is required', 'code': 400}})
    staff_id = fields.Str(required=False)
    total_rating = fields.Int(required=True,
                              error_messages={'required': {'message': 'total_rating is required', 'code': 400}})
    reservation_id = fields.Str(required=True,
                                error_messages={'required': {'message': 'reservation_id is required', 'code': 400}})
    status = fields.Str(required=True,
                        error_messages={'required': {'message': 'status is required', 'code': 400}})
    questions = fields.List(cls_or_instance=fields.Nested(SurveyQuestion), required=True,
                            error_messages={'required': {'message': 'questions is required', 'code': 400}})
    content = fields.Str(required=True,
                         error_messages={'required': {'message': 'content is required', 'code': 400}})
    platform = fields.Str(required=True,
                          error_messages={'required': {'message': 'platform is required', 'code': 400}})
