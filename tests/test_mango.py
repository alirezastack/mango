from olive.proto import zoodroom_pb2_grpc, zoodroom_pb2
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
def grpc_server(cls):
    """Instantiate a Mango server and return a stub for use in tests"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    zoodroom_pb2_grpc.add_MangoServiceServicer_to_server(cls(), server)
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

    def DeleteQuestion(self, request, context):
        return zoodroom_pb2.DeleteQuestionResponse()


class SurveyTest(unittest.TestCase):
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
        with grpc_server(FakeMangoService) as stub:
            response = stub.DeleteQuestion(zoodroom_pb2.DeleteQuestionRequest(
                question_id='12222222'
            ))
        self.assertEqual(type(response.is_deleted), bool)
        self.assertFalse(response.is_deleted)
