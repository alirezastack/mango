from olive.proto import zoodroom_pb2_grpc, health_pb2_grpc
from mango.core.store.question_store import QuestionStore
from olive.store.mongo_connection import MongoConnection
from olive.proto.health import HealthService
from mango.core.survey import MangoService
from olive.proto.rpc import GRPCServerBase
from cement.core.exc import CaughtSignal
from mango.controllers.base import Base
from olive.exc import MangoServiceError
from cement import App, TestApp


class MangoApp(App):
    """Mango primary application."""

    class Meta:
        label = 'mango'

        # configuration defaults
        # config_defaults = CONFIG

        # call sys.exit() on close
        close_on_exit = True

        # load additional framework extensions
        extensions = [
            'yaml',
            'colorlog',
            'redis',
        ]

        # configuration handler
        config_handler = 'yaml'

        cache_handler = 'redis'

        # configuration file suffix
        config_file_suffix = '.yml'

        # set the log handler
        log_handler = 'colorlog'

        # register handlers
        handlers = [
            Base
        ]

    def run(self):
        mongodb_cfg = self.config['mango']['mongodb']
        self.log.debug('initiating MongoDB configuration...')
        mongo = MongoConnection(mongodb_cfg, self)
        self.log.info('current database: {}'.format(mongo))
        target_database = mongo.service_db
        question_store = QuestionStore(target_database.question, self)
        self.log.info('current service name: ' + self._meta.label)

        # Passing self for app is suggested by Cement Core Developer:
        #   - https://github.com/datafolklabs/cement/issues/566
        cs = MangoServer(service_name=self._meta.label,
                         question_store=question_store,
                         app=self)
        cs.start()


class MangoServer(GRPCServerBase):
    def __init__(self, service_name, question_store, app):
        super(MangoServer, self).__init__(service=service_name, app=app)

        # add class to gRPC server
        service = MangoService(question_store=question_store,
                               app=app,
                               ranges=app.config['mango']['survey_setting']['ranges'])
        health_service = HealthService(app=app)

        # adds a MangoService to a gRPC.Server
        zoodroom_pb2_grpc.add_MangoServiceServicer_to_server(service, self.server)
        health_pb2_grpc.add_HealthServicer_to_server(health_service, self.server)


class MangoAppTest(TestApp, MangoApp):
    """A sub-class of MangoService that is better suited for testing."""

    class Meta:
        label = 'mango'


def main():
    with MangoApp() as app:
        try:
            app.run()
        except AssertionError as e:
            print('AssertionError > %s' % e.args[0])
            app.exit_code = 1

            if app.debug is True:
                import traceback
                traceback.print_exc()

        except MangoServiceError as e:
            print('MangoError > %s' % e.args[0])
            app.exit_code = 1

            if app.debug is True:
                import traceback
                traceback.print_exc()

        except CaughtSignal as e:
            # Default Cement signals are SIGINT and SIGTERM, exit 0 (non-error)
            print('\n%s' % e)
            app.exit_code = 0


if __name__ == '__main__':
    main()
