from olive.proto.zoodroom_pb2 import AddQuestionRequest, AddQuestionResponse
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
            self.app.log.debug('accepted fields by gRPC proto: {}'.format(request.DESCRIPTOR.fields_by_name.keys()))
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
            self.app.log.debug('question has been saved successfully: {}'.format(question_id))

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
