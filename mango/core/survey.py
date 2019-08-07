from bson.errors import InvalidId
from olive.proto.zoodroom_pb2 import AddQuestionRequest, AddQuestionResponse, GetQuestionByIdRequest, \
    GetQuestionByIdResponse, DeleteQuestionRequest, DeleteQuestionResponse, UpdateQuestionRequest, \
    UpdateQuestionResponse, AddSurveyResponse, AddSurveyRequest
from olive.exc import InvalidObjectId, DocumentNotFound, SaveError
from olive.proto import zoodroom_pb2_grpc
from marshmallow import ValidationError
from olive.proto.rpc import Response
import traceback


class MangoService(zoodroom_pb2_grpc.MangoServiceServicer):
    def __init__(self, question_store, survey_store, app, ranges):
        self.question_store = question_store
        self.survey_store = survey_store
        self.app = app
        self.ranges = ranges

    def AddSurvey(self, request: AddSurveyRequest, context) -> AddSurveyResponse:
        try:
            self.app.log.info('accepted fields by gRPC proto: {}'.format(request.DESCRIPTOR.fields_by_name.keys()))
            # TODO: Zoodroom-backend Compatibility
            questions_dict = {question.question_id: question.rating for question in request.questions}
            self.app.log.debug('Validating and retrieving questions from database')
            questions = self.question_store.get_questions_by_filters(questions_dict.keys(),
                                                                     include_in="user_rate", status="active")

            validated_question_ids = [str(q['_id']) for q in questions]
            self.app.log.info('Validation completed, validated questions: {}'.format(','.join(validated_question_ids)))

            self.app.log.debug('Validating if all the sent questions exists')
            for k in questions_dict.keys():
                if k not in validated_question_ids:
                    raise DocumentNotFound("Question {} not found".format(k))
            self.app.log.info('All the sent questions are valid')

            self.app.log.debug('Calculating total rating')
            sum = 0.0
            counter = 0.0
            overall_rate = None
            for survey_question in questions:
                sum += survey_question['weight'] * questions_dict[str(survey_question['_id'])]
                counter += survey_question['weight']
            if counter != 0:
                overall_rate = round(sum / counter, 1)

            self.app.log.info('Calculation was successful, Calculated rate: {}'.format(str(int(overall_rate))))

            survey_payload = {
                'user_id': request.user_id,
                'staff_id': request.staff_id,
                'reservation_id': request.reservation_id,
                'status': request.status,
                'content': request.content,
                'questions': [],
                'total_rating': overall_rate,
                'platform': request.platform,
            }

            for question in questions:
                if str(question['_id']) in questions_dict.keys():
                    survey_payload['questions'].append({
                        'question_id': str(question['_id']),
                        'rating': questions_dict.get(str(question['_id']), 0)
                    })

            survey_id = self.survey_store.save(survey_payload)
            self.app.log.info('survey has been saved successfully: {}'.format(survey_id))

            return Response.message(
                survey_id=survey_id
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

        except DocumentNotFound as dnf:
            self.app.log.error('question not found:\r\n{}'.format(traceback.format_exc()))
            return Response.message(
                error={
                    'code': 'resource_not_found',
                    'message': str(dnf),
                    'details': []
                }
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

    def AddQuestion(self, request: AddQuestionRequest, context) -> AddQuestionResponse:
        try:
            self.app.log.info('accepted fields by gRPC proto: {}'.format(request.DESCRIPTOR.fields_by_name.keys()))
            question_payload = {
                'title': {
                    'on_rate': request.title.on_rate,
                    'on_display': request.title.on_display,
                },
                'include_in': list(request.include_in),
                'weight': request.weight,
                'order': request.order,
                'status': request.status,
                'category': request.category
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
                ranges=self.ranges,
                category=question['category'],
                title=question['title'],
                order=question['order'],
                status=question['status'],
                include_in=question['include_in'],
                weight=question['weight']
            )
        except DocumentNotFound as dnf:
            self.app.log.error('question not found:\r\n{}'.format(traceback.format_exc()))
            return Response.message(
                error={
                    'code': 'resource_not_found',
                    'message': str(dnf),
                    'details': []
                }
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

    def UpdateQuestion(self, request: UpdateQuestionRequest, context) -> UpdateQuestionResponse:
        try:
            self.app.log.info('accepted fields by gRPC proto: {}'.format(request.DESCRIPTOR.fields_by_name.keys()))

            question = self.question_store.get_question_by_id(request.question_id)
            new_question = {
                'title': {
                    'on_rate': request.title.on_rate or question['title']['on_rate'],
                    'on_display': request.title.on_display or question['title']['on_display'],
                },
                'include_in': list(request.include_in) or question['include_in'],
                'category': request.category or question['category'],
                'status': request.status or question['status'],
                'order': request.order or question['order'],
                'weight': request.weight or question['weight'],
            }

            question = self.question_store.update(request.question_id, new_question)

            return Response.message(
                is_updated=bool(question)
            )
        except SaveError as se:
            self.app.log.error('question cannot be updated:\r\n{}'.format(traceback.format_exc()))
            return Response.message(
                error={
                    'code': 'save_error',
                    'message': str(se),
                    'details': []
                }
            )
        except DocumentNotFound as dnf:
            self.app.log.error('question not found:\r\n{}'.format(traceback.format_exc()))
            return Response.message(
                error={
                    'code': 'resource_not_found',
                    'message': str(dnf),
                    'details': []
                }
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

    def DeleteQuestion(self, request: DeleteQuestionRequest, context) -> DeleteQuestionResponse:
        try:
            self.app.log.info('accepted fields by gRPC proto: {}'.format(request.DESCRIPTOR.fields_by_name.keys()))
            delete_response = self.question_store.delete(request.question_id)
            return Response.message(
                is_deleted=bool(delete_response)
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
        except Exception:
            self.app.log.error('An error occurred: {}'.format(traceback.format_exc()))
            return Response.message(
                error={
                    'code': 'server_error',
                    'message': 'Server is in maintenance mode',
                    'details': []
                }
            )
