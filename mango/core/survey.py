from olive.exc import InvalidObjectId
from olive.proto.zoodroom_pb2 import AddQuestionRequest, AddQuestionResponse, GetQuestionByIdRequest, \
    GetQuestionByIdResponse
from olive.proto import zoodroom_pb2_grpc
from marshmallow import ValidationError
from olive.proto.rpc import Response
import traceback


class MangoService(zoodroom_pb2_grpc.MangoServiceServicer):
    def __init__(self, question_store, app):
        self.question_store = question_store
        self.app = app

    def AddQuestion(self, request: AddQuestionRequest, context) -> AddQuestionResponse:
        try:
            self.app.log.info('accepted fields by gRPC proto: {}'.format(request.DESCRIPTOR.fields_by_name.keys()))
            ranges = []
            for r in request.ranges:
                ranges.append({
                    "color": r.color,
                    "range": r.range,
                    "content": r.content
                })

            question_payload = {
                'title': {
                    'on_rate': request.title.on_rate,
                    'on_display': request.title.on_display,
                },
                'include_in': list(request.include_in),
                'weight': request.weight,
                'order': request.order,
                'status': request.status,
                'category': {
                    'title': request.category.title,
                    'icon': request.category.icon,
                    'slug': request.category.slug,
                    'order': request.category.order
                },
                "ranges": ranges
            }

            question_id = self.question_store.save(question_payload)
            self.app.log.info('question has been saved successfully: {}'.format(question_id))

            return Response.message(
                question_id=question_id
            )
        except ValueError as ve:
            self.app.log.error('Schema value error:\r\n{}'.format(traceback.format_exc()))
            return Response.message(
                error={
                    'code': 'value_error',
                    'message': str(ve),
                    'details': []
                }
            )
        except ValidationError as ve:
            self.app.log.error('Schema validation error:\r\n{}'.format(ve.messages))
            return Response.message(
                error={
                    'code': 'invalid_schema',
                    'message': 'Given data is not valid!',
                    'details': []
                }
            )
        except Exception:
            self.app.log.error('An error occurred: {}'.format(traceback.format_exc()))
            return Response.message(
                error={
                    'code': 'server_error',
                    'message': 'Server is in maintenance mode',
                    'details': []
                }
            )

    def GetQuestionById(self, request: GetQuestionByIdRequest, context) -> GetQuestionByIdResponse:
        try:
            self.app.log.info('accepted fields by gRPC proto: {}'.format(request.DESCRIPTOR.fields_by_name.keys()))
            question = self.question_store.get_question_by_id(request.question_id)
            return Response.message(
                _id=str(question['_id']),
                ranges=question.get('ranges', []),
                category=question['category'],
                title=question['title'],
                order=question['order'],
                status=question['status'],
                include_in=question['include_in'],
                weight=question['weight']
            )
        except ValueError as ve:
            self.app.log.error('Schema value error:\r\n{}'.format(traceback.format_exc()))
            return Response.message(
                error={
                    'code': 'value_error',
                    'message': str(ve),
                    'details': []
                }
            )
        except InvalidObjectId as ioi:
            self.app.log.error('Invalid ObjectId (question_id) given:\r\n{}'.format(traceback.format_exc()))
            return Response.message(
                error={
                    'code': 'invalid_id',
                    'message': str(ioi),
                    'details': []
                }
            )
        except ValidationError as ve:
            self.app.log.error('Schema validation error:\r\n{}'.format(ve.messages))
            return Response.message(
                error={
                    'code': 'invalid_schema',
                    'message': 'Given data is not valid!',
                    'details': []
                }
            )
        except Exception:
            self.app.log.error('An error occurred: {}'.format(traceback.format_exc()))
            return Response.message(
                error={
                    'code': 'server_error',
                    'message': 'Server is in maintenance mode',
                    'details': []
                }
            )
