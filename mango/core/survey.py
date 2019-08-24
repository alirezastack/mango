from olive.proto.zoodroom_pb2 import AddQuestionRequest, AddQuestionResponse, GetQuestionByIdRequest, \
    GetQuestionByIdResponse, DeleteQuestionRequest, DeleteQuestionResponse, UpdateQuestionRequest, \
    AddSurveyResponse, AddSurveyRequest, UpdateQuestionResponse, GetQuestionsRequest, GetQuestionsResponse, \
    GetSurveyByReservationIdRequest, GetSurveyByReservationIdResponse, GetSurveysRequest, GetSurveysResponse, \
    StreamGetSurveysResponse, StreamGetSurveysRequest
from olive.exc import InvalidObjectId, DocumentNotFound, SaveError, FetchError
from olive.store.toolbox import int_to_object_id
from olive.proto import zoodroom_pb2_grpc
from marshmallow import ValidationError
from olive.proto.rpc import Response
from olive.http import Request
import traceback


class MangoService(zoodroom_pb2_grpc.MangoServiceServicer):
    def __init__(self, question_store, survey_store, app, ranges, legacy_url, legacy_key):
        self.question_store = question_store
        self.survey_store = survey_store
        self.app = app
        self.ranges = ranges
        self.legacy_base_url = legacy_url if legacy_url[-1:] == '/' else '{}/'.format(legacy_url)
        self.legacy_key = legacy_key

    def AddSurvey(self, request: AddSurveyRequest, context) -> AddSurveyResponse:
        try:
            self.app.log.info('accepted fields by gRPC proto: {}'.format(request.DESCRIPTOR.fields_by_name.keys()))
            given_questions = {question.question_id: question.rating for question in request.questions}
            self.app.log.debug('Validating and retrieving below questions from database: \n{}'.format(given_questions))
            questions = self.question_store.get_questions_by_filters(question_ids=given_questions.keys(),
                                                                     include_in="user_rate",
                                                                     status="active",
                                                                     project=['weight'])
            db_question_ids = [str(q['_id']) for q in questions]
            self.app.log.info('Validation completed, validated questions: {}'.format(','.join(db_question_ids)))

            self.app.log.debug('Validating if all the sent questions exists')
            for k in given_questions.keys():
                if k not in db_question_ids:
                    raise DocumentNotFound("question {} not found with status=`active` and include_in=`user_rate`".format(k))

            self.app.log.info('all questions are valid')

            self.app.log.debug('calculating total rating...')
            sum_of_survey = 0.0
            counter = 0.0
            for question in questions:
                sum_of_survey += question['weight'] * given_questions[str(question['_id'])]
                counter += question['weight']

            overall_rate = int(round(sum_of_survey / counter, 1)) if counter else None
            self.app.log.info('survey total_rating: {}/{} => {}'.format(sum_of_survey, counter, overall_rate))

            survey_payload = {
                'user_id': request.user_id,
                'staff_id': request.staff_id,
                'reservation_id': request.reservation_id,
                'status': request.status,
                'content': request.content,
                'questions': [{"question_id": q, "rating": r or 0} for q, r in given_questions.items()],
                'total_rating': overall_rate,
                'platform': request.platform,
            }

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

    def GetQuestions(self, request: GetQuestionsRequest, context) -> GetQuestionsResponse:
        try:
            self.app.log.info('accepted fields by gRPC proto: {}'.format(request.DESCRIPTOR.fields_by_name.keys()))
            questions = self.question_store.get_questions()
            return Response.message(questions=questions)
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

    def GetSurveyByReservationId(self, request: GetSurveyByReservationIdRequest, context) -> GetSurveyByReservationIdResponse:
        try:
            self.app.log.info('accepted fields by gRPC proto: {}'.format(request.DESCRIPTOR.fields_by_name.keys()))
            survey = self.survey_store.get_by_reservation_id(request.reservation_id)
            return Response.message(_id=survey['_id'],
                                    questions=survey['questions'],
                                    user_id=survey['user_id'],
                                    staff_id=survey['staff_id'],
                                    reservation_id=survey['reservation_id'],
                                    status=survey['status'],
                                    content=survey['content'],
                                    platform=survey['platform'],
                                    total_rating=survey['total_rating'])
        except ValueError as ve:
            self.app.log.error('Schema value error:\r\n{}'.format(traceback.format_exc()))
            return Response.message(
                error={
                    'code': 'value_error',
                    'message': str(ve),
                    'details': []
                }
            )
        except DocumentNotFound as dnf:
            self.app.log.error('survey not found:\r\n{}'.format(traceback.format_exc()))
            return Response.message(
                error={
                    'code': 'resource_not_found',
                    'message': str(dnf),
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

    def StreamGetSurveys(self, request: StreamGetSurveysRequest, context) -> StreamGetSurveysResponse:
        try:
            for survey in self.survey_store.stream_surveys():
                yield Response.message(survey=survey)
        except ValidationError as ve:
            self.app.log.error('Schema validation error:\r\n{}'.format(ve.messages))
            yield Response.message(
                error={
                    'code': 'invalid_schema',
                    'message': 'Given data is not valid!',
                    'details': []
                }
            )
        except Exception:
            self.app.log.error('An error occurred: {}'.format(traceback.format_exc()))
            yield Response.message(
                error={
                    'code': 'server_error',
                    'message': 'Server is in maintenance mode',
                    'details': []
                }
            )

    def GetSurveys(self, request: GetSurveysRequest, context) -> GetSurveysResponse:
        try:
            self.app.log.info('accepted fields by gRPC proto: {}'.format(request.DESCRIPTOR.fields_by_name.keys()))
            query = {}
            if not all(v is None for v in [request.checkout_start,
                                           request.checkout_end,
                                           request.city,
                                           request.complex]):
                url = '{}v3/internal-reservations'.format(self.legacy_base_url)
                params = []
                if request.checkout_start:
                    params.append('checkout_start={}'.format(request.checkout_start))
                if request.checkout_end:
                    params.append('checkout_end={}'.format(request.checkout_end))
                if request.complex:
                    params.append('complex={}'.format(request.complex))
                if request.city:
                    params.append('city={}'.format(request.city))

                url = '{}?{}'.format(url, '&'.join(params))

                rq = Request(url=url,
                             app=self.app,
                             headers={'X-INTERNAL-API-KEY': self.legacy_key})
                reservations = rq.get()
                if reservations:
                    reservations = list(map(int_to_object_id, reservations))
                    query = {'reservation_id': {'$in': reservations}}

                status = request.status
                if status:
                    query['status'] = status.lower()

            total_count, surveys = self.survey_store.get_surveys(skip=request.skip,
                                                                 limit=request.page_size,
                                                                 query=query)
            self.app.log.info('total surveys count: {}'.format(total_count))
            return Response.message(
                surveys=surveys,
                total_count=total_count
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
        except FetchError as fe:
            self.app.log.error('Legacy API error:\r\n{}'.format(traceback.format_exc()))
            return Response.message(
                error={
                    'code': 'legacy_fetch_error',
                    'message': 'Could not get data from Legacy API!',
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
