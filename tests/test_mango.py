from olive.store.mongo_connection import MongoConnection
from olive.proto import zoodroom_pb2_grpc, zoodroom_pb2
from mango.core.store.question import QuestionStore
from mango.core.store.survey import SurveyStore
from mango.core.survey import MangoService
from decorator import contextmanager
from mango.main import MangoAppTest
from concurrent import futures
import unittest
import grpc


def test_mango():
    # test mango without any subcommands or arguments
    with MangoAppTest(config_files=['/etc/mango/mango.yml']) as app:
        app.run()
        assert app.exit_code == 0


def test_mango_debug():
    # test that debug mode is functional
    argv = ['--debug']
    with MangoAppTest(argv=argv) as app:
        app.run()
        assert app.debug is True


def test_command1():
    # test command1 without arguments
    argv = ['command1']
    with MangoAppTest(argv=argv) as app:
        app.run()
        data, output = app.last_rendered
        assert data['foo'] == 'bar'
        assert output.find('Foo => bar')

    # test command1 with arguments
    argv = ['command1', '--foo', 'not-bar']
    with MangoAppTest(argv=argv) as app:
        app.run()
        data, output = app.last_rendered
        assert data['foo'] == 'not-bar'
        assert output.find('Foo => not-bar')


@contextmanager
def grpc_server(cls, question_store, survey_store, app, ranges, url, key):
    """Instantiate a Mango server and return a stub for use in tests"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    zoodroom_pb2_grpc.add_MangoServiceServicer_to_server(cls(question_store, survey_store, app, ranges, url, key), server)
    port = server.add_insecure_port('[::]:0')
    server.start()

    try:
        with grpc.insecure_channel('localhost:%d' % port) as channel:
            yield zoodroom_pb2_grpc.MangoServiceStub(channel)
    finally:
        server.stop(None)


class SurveyTest(unittest.TestCase):
    def setUp(self):
        # with MangoAppTest(config_files=['/etc/mango/mango.yml']) as app:
        self.app = MangoAppTest(config_files=['/etc/mango/mango.yml'])
        self.app.__enter__()
        mongodb_cfg = self.app.config['mango']['mongodb']
        mongo = MongoConnection(mongodb_cfg, self.app)
        target_database = mongo.service_db
        self.ranges = self.app.config['mango']['survey_setting']['ranges']
        self.legacy_url = self.app.config['mango']['legacy']['base_url']
        self.legacy_key = self.app.config['mango']['legacy']['key']
        self.question_store = QuestionStore(target_database.question, self.app)
        self.survey_store = SurveyStore(target_database.survey, self.app)
        self.grpc_server = grpc_server(MangoService, self.question_store, self.survey_store,
                                       self.app, self.ranges, self.legacy_url, self.legacy_key)

    def test_successful_add_question(self):
        with grpc_server(MangoService, self.question_store, self.survey_store, self.app,
                         self.ranges, self.legacy_url, self.legacy_key) as stub:
            response = stub.AddQuestion(zoodroom_pb2.AddQuestionRequest(
                title=zoodroom_pb2.QuestionTitle(on_rate='on rate',
                                                 on_display='on-display'),
                include_in=['rate_display'],
                weight=2,
                order=1
            ))
            self.assertNotEqual(response.question_id, '')

    def test_invalid_grpc_field_in_add_question(self):
        try:
            with grpc_server(MangoService, self.question_store, self.survey_store, self.app,
                             self.ranges, self.legacy_url, self.legacy_key) as stub:
                self.assertRaises(ValueError, stub.AddQuestion(zoodroom_pb2.AddQuestionRequest(
                    invalid_field=12
                )))
        except ValueError:
            pass
        except Exception:
            self.fail('Expected exception not raised!')

    def test_delete_question(self):
        with grpc_server(MangoService, self.question_store, self.survey_store, self.app,
                         self.ranges, self.legacy_url, self.legacy_key) as stub:
            response = stub.DeleteQuestion(zoodroom_pb2.DeleteQuestionRequest(
                question_id='12222222'
            ))
            self.assertEqual(response.error.code, 'invalid_id')

    def test_add_survey(self):
        with grpc_server(MangoService, self.question_store, self.survey_store, self.app,
                         self.ranges, self.legacy_url, self.legacy_key) as stub:
            response = stub.AddSurvey(zoodroom_pb2.AddSurveyRequest(
                questions=[zoodroom_pb2.SurveyQuestion(
                    question_id='5d4bbd9cf9c3ca6feb2563b3',
                    rating=2
                ), zoodroom_pb2.SurveyQuestion(
                    question_id='5d4bbda3f9c3ca6feb2563b4',
                    rating=3
                )]
            ))
            self.assertEqual(len(response.survey_id), 24)

    def test_add_survey_with_invalid_question_id(self):
        with grpc_server(MangoService, self.question_store, self.survey_store,
                         self.app, self.ranges, self.legacy_url, self.legacy_key) as stub:
            response = stub.AddSurvey(zoodroom_pb2.AddSurveyRequest(
                questions=[zoodroom_pb2.SurveyQuestion(
                    question_id='5d4bbd9cf9c3ca6feb2563b0',
                    rating=2
                ), zoodroom_pb2.SurveyQuestion(
                    question_id='5d4bbda3f9c3ca6feb2563b4',
                    rating=3
                )]
            ))
            self.assertEqual(response.error.code, 'resource_not_found')

    def test_get_survey_by_reservation_id(self):
        with grpc_server(MangoService, self.question_store, self.survey_store, self.app,
                         self.ranges, self.legacy_url, self.legacy_key) as stub:
            response = stub.GetSurveyByReservationId(zoodroom_pb2.GetSurveyByReservationIdRequest(
                reservation_id='12'
            ))
            self.assertEqual(response.reservation_id, '12')

    def test_get_survey_by_invalid_reservation_id(self):
        with grpc_server(MangoService, self.question_store, self.survey_store, self.app,
                         self.ranges, self.legacy_url, self.legacy_key) as stub:
            response = stub.GetSurveyByReservationId(zoodroom_pb2.GetSurveyByReservationIdRequest(
                reservation_id='non_existent_id'
            ))
            self.assertEqual(response.error.code, 'resource_not_found')

    def test_get_surveys(self):
        with grpc_server(MangoService, self.question_store, self.survey_store, self.app,
                         self.ranges, self.legacy_url, self.legacy_key) as stub:
            response = stub.GetSurveys(zoodroom_pb2.GetSurveysRequest(
                skip=700000,
                limit=1
            ))
            print(response.surveys)
        self.assertEqual(type(response.total_count), int)
        self.assertEqual(len(list(response.surveys)), 0)

    def test_update_question(self):
        with grpc_server(MangoService, self.question_store, self.survey_store, self.app,
                         self.ranges, self.legacy_url, self.legacy_key) as stub:
            response = stub.UpdateQuestion(zoodroom_pb2.UpdateQuestionRequest(
                question_id='12222222',
                title=zoodroom_pb2.QuestionTitle(on_rate='blah rate',
                                                 on_display='blah display'),
                include_in=['something'],
                order=20,
                weight=12
            ))
        self.assertEqual(type(response.is_updated), bool)
        self.assertFalse(response.is_updated)

    def test_stream_get_surveys(self):
        with grpc_server(MangoService, self.question_store, self.survey_store, self.app,
                         self.ranges, self.legacy_url, self.legacy_key) as stub:
            stub.AddSurvey(zoodroom_pb2.AddSurveyRequest(
                questions=[zoodroom_pb2.SurveyQuestion(
                    question_id='5d4bbd9cf9c3ca6feb2563b3',
                    rating=2
                ), zoodroom_pb2.SurveyQuestion(
                    question_id='5d4bbda3f9c3ca6feb2563b4',
                    rating=3
                )],
                reservation_id='my-unique-reservation'
            ))

            response = stub.StreamGetSurveys(zoodroom_pb2.StreamGetSurveysRequest())
            rid = None
            for res in response:
                if res.survey.reservation_id == 'my-unique-reservation':
                    rid = res.survey.reservation_id
                    break

            self.assertEqual(rid, 'my-unique-reservation')

    def test_get_questions(self):
        with grpc_server(MangoService, self.question_store, self.survey_store, self.app,
                         self.ranges, self.legacy_url, self.legacy_key) as stub:
            request = zoodroom_pb2.GetQuestionsRequest()
            question = {
                'title': zoodroom_pb2.QuestionTitle(on_rate='on rate'),
                'include_in': ['rate_display', ], 'weight': 0, 'order': 3
            }

            add_response = stub.AddQuestion(zoodroom_pb2.AddQuestionRequest(**question))
            added_id = add_response.question_id
            question['_id'] = added_id

            get_response = stub.GetQuestions(request=request)
            self.assertIsInstance(get_response, zoodroom_pb2.GetQuestionsResponse)
            for question in get_response.questions:
                self.assertIsInstance(question, zoodroom_pb2.Question)

            self.assertIn(question, get_response.questions)

            deletion_response = stub.DeleteQuestion(
                zoodroom_pb2.DeleteQuestionRequest(question_id=added_id))
            get_questions_response = stub.GetQuestions(request=request)
            if deletion_response.is_deleted:
                self.assertNotIn(question, get_questions_response.questions)
