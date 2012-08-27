#
# Copyright 2012 SAS Institute
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

from cStringIO import StringIO

import mock
import sys
import testutils

from bigitr import errhandler, context, appconfig

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
            self.ctx.mails['repo1'].addAttachment = mock.Mock()
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

            self.ctx.mails['repo1'].addAttachment.assert_called_once_with(
                mock.ANY, 'Traceback')
            self.ctx.logs['repo1'].writeError.assert_called_once()
            self.assertTrue(
                self.ctx.logs['repo1'].writeError.call_args[0][0].startswith(
                    "Error for repository 'repo1':\nTraceback"))

    def test_reportContinue(self):
        with mock.patch('sys.stderr') as e:
            self.ctx.logs['repo1'].writeError = mock.Mock()
            self.ctx.mails['repo1'].addAttachment = mock.Mock()
            try:
                self.inner()
            except:
                pass
            self.err.report('repo1', action=appconfig.CONTINUE)
            e.write.assert_not_called()
            e.flush.assert_not_called()

            self.ctx.mails['repo1'].addAttachment.assert_called_once_with(
                mock.ANY, 'Traceback')
            self.ctx.logs['repo1'].writeError.assert_called_once()
            self.assertTrue(
                self.ctx.logs['repo1'].writeError.call_args[0][0].startswith(
                    "Error for repository 'repo1':\nTraceback"))
