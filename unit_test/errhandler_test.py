from cStringIO import StringIO

import mock
import sys
import testutils

from gitcvs import errhandler, context, appconfig

class TestErrors(testutils.TestCase):
    def setUp(self):
        appConfig = StringIO('''
[import]
[global]
''')
        repConfig = StringIO('''
[repo1]
''')
        self.ctx = context.Context(appConfig, repConfig)
        self.ctx.logs['repo1'] = mock.Mock()
        self.err = errhandler.Errors(self.ctx)

    @staticmethod
    def inner():
        1/0

    def test_abort(self):
        self.err.report = mock.Mock()
        try:
            self.inner()
        except:
            pass
        self.assertRaises(ZeroDivisionError,
            self.err, 'repo1', appconfig.ABORT)
        self.err.report.assert_not_called()

    def test_warn(self):
        self.err.report = mock.Mock()
        try:
            self.inner()
        except:
            pass
        self.err('repo1', appconfig.WARN)
        self.err.report.assert_called_once_with('repo1', mock.ANY, appconfig.WARN)

    def test_continue(self):
        self.err.report = mock.Mock()
        try:
            self.inner()
        except:
            pass
        self.err('repo1', appconfig.CONTINUE)
        self.err.report.assert_called_once_with('repo1', mock.ANY, appconfig.CONTINUE)

    def test_report(self):
        with mock.patch('sys.stderr') as e:
            self.ctx.logs['repo1'].writeError = mock.Mock()
            try:
                self.inner()
            except:
                pass
            self.err.report('repo1')

            e.write.assert_called_once()
            self.assertTrue(
                e.write.call_args[0][0].startswith(
                    "Error for repository 'repo1':\nTraceback"))
            e.flush.assert_called_once_with()

            self.ctx.logs['repo1'].writeError.assert_called_once()
            self.assertTrue(
                self.ctx.logs['repo1'].writeError.call_args[0][0].startswith(
                    "Error for repository 'repo1':\nTraceback"))

    def test_reportContinue(self):
        with mock.patch('sys.stderr') as e:
            self.ctx.logs['repo1'].writeError = mock.Mock()
            try:
                self.inner()
            except:
                pass
            self.err.report('repo1', action=appconfig.CONTINUE)
            e.write.assert_not_called()
            e.flush.assert_not_called()

            self.ctx.logs['repo1'].writeError.assert_called_once()
            self.assertTrue(
                self.ctx.logs['repo1'].writeError.call_args[0][0].startswith(
                    "Error for repository 'repo1':\nTraceback"))
