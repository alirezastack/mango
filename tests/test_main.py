from mango.main import MangoAppTest


def test_mango(tmp):
    with MangoAppTest() as app:
        res = app.run()
        print(res)
        raise Exception


def test_command1(tmp):
    argv = ['command1']
    with MangoAppTest(argv=argv) as app:
        app.run()
