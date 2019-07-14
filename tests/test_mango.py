from concurrent import futures

import grpc
from decorator import contextmanager
from olive.proto import zoodroom_pb2_grpc, zoodroom_pb2

from mango.main import MangoAppTest
import unittest


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
def add_question(cls):
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


class SurveyTest(unittest.TestCase):
    def test_add_question(self):
        # may do something extra for this mock if it's stateful
        class FakeAddQuestion(zoodroom_pb2_grpc.MangoServiceServicer):
            def AddQuestion(self, request, context):
                return zoodroom_pb2.AddQuestionResponse()

        with add_question(FakeAddQuestion) as stub:
            response = stub.AddQuestion(zoodroom_pb2.AddQuestionRequest(
                title=zoodroom_pb2.QuestionTitle(on_rate='on rate',
                                                 on_display='on-display')))
            self.assertEqual(response.question_id, '')
