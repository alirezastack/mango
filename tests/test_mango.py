from mango.core.store.question_store import QuestionStore
from olive.store.mongo_connection import MongoConnection
from olive.proto import zoodroom_pb2_grpc, zoodroom_pb2

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
def grpc_server(cls, question_store, app, ranges):
    """Instantiate a Mango server and return a stub for use in tests"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    zoodroom_pb2_grpc.add_MangoServiceServicer_to_server(cls(question_store, app, ranges), server)
    port = server.add_insecure_port('[::]:0')
    server.start()

    try:
        with grpc.insecure_channel('localhost:%d' % port) as channel:
            yield zoodroom_pb2_grpc.MangoServiceStub(channel)
    finally:
        server.stop(None)


# may do something extra for this mock if it's stateful
class FakeMangoService(zoodroom_pb2_grpc.MangoServiceServicer):
    def AddQuestion(self, request, context):
        return zoodroom_pb2.AddQuestionResponse()

    def AddSurvey(self, request, context):
        return zoodroom_pb2.AddSurveyResponse()

    def DeleteQuestion(self, request, context):
        return zoodroom_pb2.DeleteQuestionResponse()


class SurveyTest(unittest.TestCase):
    def setUp(self):
        # with MangoAppTest(config_files=['/etc/mango/mango.yml']) as app:
        self.app = MangoAppTest(config_files=['/etc/mango/mango.yml'])
        self.app.__enter__()
        mongodb_cfg = self.app.config['mango']['mongodb']
        mongo = MongoConnection(mongodb_cfg, self.app)
        target_database = mongo.service_db
        self.ranges = self.app.config['mango']['survey_setting']['ranges']
        self.question_store = QuestionStore(target_database.question, self.app)
        self.survey_store = SurveyStore(target_database.survey, self.app)
        self.grpc_server = grpc_server(MangoService, self.question_store, self.app, self.ranges)

    def test_successful_add_question(self):
        with grpc_server(FakeMangoService) as stub:
            response = stub.AddQuestion(zoodroom_pb2.AddQuestionRequest(
                title=zoodroom_pb2.QuestionTitle(on_rate='on rate',
                                                 on_display='on-display'),
                include_in=['rate_display'],
                weight=2,
                order=1,
                status='active',
                category='customer_survey'
            ))
            self.assertEqual(response.question_id, '')

    def test_invalid_grpc_field_in_add_question(self):
        try:
            with grpc_server(FakeMangoService) as stub:
                self.assertRaises(ValueError, stub.AddQuestion(zoodroom_pb2.AddQuestionRequest(
                    invalid_field=12
                )))
        except ValueError:
            pass
        except Exception:
            self.fail('Expected exception not raised!')

    def test_delete_question(self):
        with grpc_server(MangoService, self.question_store, self.app, self.ranges) as stub:
            response = stub.DeleteQuestion(zoodroom_pb2.DeleteQuestionRequest(
                question_id='12222222'
            ))
            self.assertEqual(response.error.code, 'invalid_id')

    def test_update_question(self):
        with grpc_server(FakeMangoService) as stub:
            response = stub.UpdateQuestion(zoodroom_pb2.UpdateQuestionRequest(
                question_id='12222222',
                title=zoodroom_pb2.QuestionTitle(on_rate='blah rate',
                                                 on_display='blah display'),
                include_in=['something'],
                category='cat',
                status='active',
                order=20,
                weight=12
            ))
        self.assertEqual(type(response.is_updated), bool)
        self.assertFalse(response.is_updated)
