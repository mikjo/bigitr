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

import asyncore
import mock
import os
import signal
import smtpd
import tempfile

import testutils

from bigitr import mail, context

class FakeSMTPServer(smtpd.SMTPServer):
    def __init__(self, dir, *args, **kwargs):
        self.basedir = dir
        smtpd.SMTPServer.__init__(self, *args, **kwargs)

    def process_message(self, peer, mailfrom, rcpttos, data):
        file(self.basedir + '/data', 'w').write(data)

class TestMail(testutils.TestCase):
    def setUp(self):
        self.logdir = tempfile.mkdtemp(suffix='.bigitr')
        self.pid = None
        appConfig = StringIO('''
[global]
mailfrom = send@er
smarthost = localhost:16294
logdir = %s''' %self.logdir)

        repConfig = StringIO('''
[repo1]
email = re@cip1 re@cip2
[repo2]
''')
        self.ctx = context.Context(appConfig, repConfig)

    def startSendmail(self):
        self.pid = os.fork()
        if not self.pid:
            FakeSMTPServer(self.logdir, ('localhost', 16294), ('localhost', 0))
            asyncore.loop()

    def tearDown(self):
        if self.pid:
            os.kill(self.pid, signal.SIGKILL)
        self.removeRecursive(self.logdir)

    def test_noRecipient(self):
        m = self.ctx.mails['repo2']
        self.assertEqual(m.ignore, True)
        with mock.patch('bigitr.mail.Email.addAttachment'):
            m.addOutput('foo', 'out', 'err')
            m.addAttachment.assert_not_called()

    def test_noMailFrom(self):
        self.ctx._ac.remove_option('global', 'mailfrom')
        m = self.ctx.mails['repo1']
        self.assertEqual(m.ignore, True)
        with mock.patch('bigitr.mail.Email.addAttachment'):
            m.addOutput('foo', 'out', 'err')
            m.addAttachment.assert_not_called()

    def test_recipient(self):
        m = self.ctx.mails['repo1']
        self.assertEqual(m.ignore, False)
        self.assertEqual(m.msg['Subject'], 'repo1: bigitr error report')
        self.assertEqual(m.msg['From'], 'send@er')
        self.assertEqual(m.msg['To'], 're@cip1, re@cip2')
        self.assertEqual(m.recipients, ['re@cip1', 're@cip2'])
        self.assertEqual(m.repo, 'repo1')
        self.assertEqual(len(m.msg.get_payload()), 0)
        m.addOutput('foo', 'out', 'err')
        self.assertEqual(len(m.msg.get_payload()), 2)
        m.addAttachment('one', 'test of  "quotes" And spec1al$')
        self.assertEqual(len(m.msg.get_payload()), 3)
        s = m.msg.as_string()
        self.assertTrue('filename="errors_from_foo.txt"' in s)
        self.assertTrue('filename="output_from_foo.txt"' in s)
        self.assertTrue('filename="test_of_quotes_And_spec1al.txt"' in s)
        self.assertFalse('filename="all_errors.txt"' in s)
        self.assertFalse('filename="all_output.txt"' in s)

        with mock.patch('bigitr.mail.Email._send'):
            m.send('all\noutput', 'all\nerrors')
            self.assertEqual(len(m.msg.get_payload()), 5)
            s = m.msg.as_string()
            self.assertTrue('filename="all_errors.txt"' in s)
            self.assertTrue('filename="all_output.txt"' in s)

    def test_sendWithEmptyBody(self):
        with mock.patch('smtplib.SMTP') as s:
            server = s.return_value
            m = self.ctx.mails['repo1']
            self.assertEqual(self.ctx.mails.keys(), ['repo1'])
            m.send('all\noutput', 'all\nerrors')
            server.sendmail.assert_not_called()
            server.quit.assert_not_called()
            self.assertEqual(self.ctx.mails.keys(), [])

    def test__send(self):
        with mock.patch('smtplib.SMTP') as s:
            server = s.return_value
            m = self.ctx.mails['repo1']
            self.assertEqual(self.ctx.mails.keys(), ['repo1'])
            m.addOutput('badcommand', 'bad\noutput', 'bad\nerrors')
            m.send('all\noutput', 'all\nerrors')
            server.sendmail.assert_called_with(
                'send@er', ['re@cip1', 're@cip2'], mock.ANY)
            server.quit.assert_called_with()
            self.assertEqual(self.ctx.mails.keys(), [])

    def test__send_through(self):
        self.startSendmail()
        msgName = self.logdir + '/data'
        self.assertFalse(os.path.exists(msgName))
        m = self.ctx.mails['repo1']
        m.addOutput('badcommand', 'bad\noutput', 'bad\nerrors')
        m.send('all\noutput', 'all\nerrors')
        self.assertTrue(os.path.exists(msgName))
        msg = file(msgName).read()
        self.assertTrue('\nSubject: repo1: bigitr error report\n' in msg)
        self.assertTrue('\n\nBigitr error report for repository repo1\n' in msg)
        self.assertTrue('attachment; filename="errors_from_badcommand.txt"\n' in msg)
        self.assertTrue('\n\nbad\nerrors\n' in msg)
        self.assertTrue('attachment; filename="output_from_badcommand.txt"\n' in msg)
        self.assertTrue('\n\nbad\noutput\n' in msg)
        self.assertTrue('attachment; filename="all_errors.txt"\n' in msg)
        self.assertTrue('\n\nall\nerrors\n' in msg)
        self.assertTrue('attachment; filename="all_output.txt"\n' in msg)
        self.assertTrue('\n\nall\noutput\n' in msg)
