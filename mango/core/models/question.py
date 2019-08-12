from olive.store.toolbox import MongoObjectId, BaseSchema
from olive.toolbox import MarshmallowDateTimeField
from marshmallow import Schema, fields, EXCLUDE
from olive.consts import UTC_DATE_FORMAT
import datetime


class TitleNestedSchema(Schema):
    on_rate = fields.Str(required=True,
                         error_messages={'required': {'message': 'question on_rate title required', 'code': 400}})
    on_display = fields.Str(required=True,
                            error_messages={'required': {'message': 'question on_display title required', 'code': 400}})


class QuestionSchema(BaseSchema):
    class Meta:
        # Tuple or list of fields to include in the serialized result
        fields = ("_id", "title", "include_in", "weight", "order", "status", "category", "ranges", "created_at")
        # exclude unknown fields from database on .load() call
        unknown = EXCLUDE
        datetimeformat = UTC_DATE_FORMAT

    title = fields.Nested(TitleNestedSchema)
    include_in = fields.List(cls_or_instance=fields.Str(),
                             default=['user_rate', 'rate_display'])
    weight = fields.Integer(required=True,
                            error_messages={'required': {'message': 'weight required', 'code': 400}})
    order = fields.Integer(required=True,
                           error_messages={'required': {'message': 'order required', 'code': 400}})
    status = fields.Str(required=True,
                        default='inactive',
                        error_messages={'required': {'message': 'status required', 'code': 400}})
    category = fields.Str(required=True,
                          error_messages={'required': {'message': 'category required', 'code': 400}})
    # dump_only: Fields to skip during deserialization(i.e.: .load())
    created_at = MarshmallowDateTimeField(dump_only=True,
                                          default=lambda: datetime.datetime.utcnow(),
                                          allow_none=False)
    _id = MongoObjectId(allow_none=False)
