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

import mock
import os
from cStringIO import StringIO
import signal
import tempfile

import testutils

from bigitr import bigitrdaemon
from bigitr import Synchronize


class TestDaemon(testutils.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(suffix='.bigitr')
        os.environ['DDIR'] = self.dir
        self.daemonConfig = self.dir + '/daemon'
        file(self.daemonConfig, 'w').write('''
[GLOBAL]
appconfig = ${DDIR}/app1
email = other@other blah@blah
mailfrom = sender@here
[foo]
repoconfig = ${DDIR}/foo1.* ${DDIR}/foo2.*
[bar]
appconfig = ${DDIR}/app2
repoconfig = ${DDIR}/bar
''')

        appCfgText = '''
[global]
[import]
[export]
'''
        app1Cfg = self.dir + '/app1'
        file(app1Cfg, 'w').write(appCfgText)
        app2Cfg = self.dir + '/app2'
        file(app2Cfg, 'w').write(appCfgText)

        repCfgText = '''
[%s]
'''
        file(self.dir + '/foo1.1', 'w').write(repCfgText % 'foo1.1')
        file(self.dir + '/foo1.2', 'w').write(repCfgText % 'foo1.2')
        file(self.dir + '/foo2.1', 'w').write(repCfgText % 'foo2.1')
        file(self.dir + '/bar', 'w').write(repCfgText % 'bar')

        self.pidFile = self.dir+'/pid'
        self.oldcwd = os.getcwd()
        os.chdir(self.dir)

    def tearDown(self):
        os.chdir(self.oldcwd)
        self.removeRecursive(self.dir)
        os.unsetenv('DDIR')

    @mock.patch('bigitr.bigitrdaemon.Daemon.createContext')
    def test_init(self, cC):
        d = bigitrdaemon.Daemon('/foo', self.daemonConfig, False, self.pidFile)
        self.assertFalse(os.path.exists(self.pidFile))
        self.assertEquals(d.execPath, '/foo')
        self.assertEquals(d.config, self.daemonConfig)
        self.assertEquals(d.pidfile, self.pidFile)
        self.assertFalse(d.restart)
        self.assertFalse(d.stop)
        cC.assert_called_once_with(False)

    @mock.patch.multiple('daemon.daemon',
        close_all_open_files=mock.DEFAULT,
        redirect_stream=mock.DEFAULT,
        register_atexit_function=mock.DEFAULT,
        change_working_directory=mock.DEFAULT,
        set_signal_handlers=mock.DEFAULT
        )
    def test_Context(self, **patches):
        d = bigitrdaemon.Daemon('/foo', self.daemonConfig, False, self.pidFile)
        self.assertFalse(os.path.exists(self.pidFile))
        self.assertFalse(d.context.pidfile.is_locked())
        with d.context:
            self.assertEqual(os.getpid(), d.context.pidfile.pid)
            self.assertTrue(d.context.pidfile.is_locked())
        self.assertFalse(d.context.pidfile.is_locked())
        self.assertEqual(d.context.detach_process, False)
        self.assertEqual(d.context.working_directory, os.getcwd())
        self.assertEqual(d.context.signal_map[signal.SIGHUP], d.sighup)
        self.assertEqual(d.context.signal_map[signal.SIGTERM], d.sigterm)
        self.assertEqual(d.context.signal_map[signal.SIGCHLD], d.sigchld)

    @mock.patch('bigitr.bigitrdaemon.Daemon.createContext')
    def test_createSynchronizers(self, cC):
        d = bigitrdaemon.Daemon('/foo', self.daemonConfig, False, self.pidFile)
        self.assertEqual(len(d.synchronizers), 4)
        for s in d.synchronizers:
            self.assertTrue(isinstance(s, Synchronize))
            for repo in s.ctx.getRepositories():
                email = s.ctx.getEmail(repo)
                if email is not None:
                    self.assertFalse('a@b' in email)

    @mock.patch('bigitr.bigitrdaemon.Daemon.createContext')
    def test_createSynchronizersAddEmail(self, cC):
        cfg = file(self.daemonConfig).read()
        cfg = cfg.replace('email = other@other blah@blah\n', '')
        cfg = cfg.replace('[GLOBAL]', '[GLOBAL]\nmailall = true\nemail = a@b')
        file(self.daemonConfig, 'w').write(cfg)
        d = bigitrdaemon.Daemon('/foo', self.daemonConfig, False, self.pidFile)
        self.assertEqual(len(d.synchronizers), 4)
        for s in d.synchronizers:
            self.assertTrue(isinstance(s, Synchronize))
            for repo in s.ctx.getRepositories():
                self.assertTrue('a@b' in s.ctx.getEmail(repo))

    @mock.patch('bigitr.bigitrdaemon.Daemon.mainLoop')
    @mock.patch.multiple('daemon.daemon',
        close_all_open_files=mock.DEFAULT,
        redirect_stream=mock.DEFAULT,
        register_atexit_function=mock.DEFAULT,
        change_working_directory=mock.DEFAULT,
        set_signal_handlers=mock.DEFAULT
        )
    def test_run(self, mainLoop, **patches):
        def assertPidFileContents():
            self.assertEqual(os.getpid(), int(file(d.pidfile).read()))
            self.assertTrue(d.context.pidfile.is_locked())
        mainLoop.side_effect = assertPidFileContents
        d = bigitrdaemon.Daemon('/foo', self.daemonConfig, False, self.pidFile)
        self.assertFalse(os.path.exists(self.pidFile))
        self.assertFalse(d.context.pidfile.is_locked())
        d.run()
        self.assertFalse(os.path.exists(self.pidFile))
        self.assertFalse(d.context.pidfile.is_locked())

    @mock.patch('bigitr.bigitrdaemon.Daemon.__init__')
    def test_sigterm(self, I):
        I.return_value = None
        d = bigitrdaemon.Daemon()
        d.stop = False
        d.sigterm(signal.SIGTERM, None)
        self.assertEqual(d.stop, True)

    @mock.patch('bigitr.bigitrdaemon.Daemon.__init__')
    def test_sighup(self, I):
        I.return_value = None
        d = bigitrdaemon.Daemon()
        d.restart = False
        d.sighup(signal.SIGHUP, None)
        self.assertEqual(d.restart, True)

    @mock.patch('bigitr.bigitrdaemon.Daemon.__init__')
    def test_sigchld(self, I):
        I.return_value = None
        d = bigitrdaemon.Daemon()
        d.sigchld(signal.SIGCHLD, None)

    @mock.patch('bigitr.bigitrdaemon.Daemon.__init__')
    def test_runOnce(self, I):
        I.return_value = None
        d = bigitrdaemon.Daemon()
        s = mock.Mock()
        d.stop = False
        d.restart = False
        d.synchronizers = [s]
        d.runOnce()
        s.run.assert_called_once_with(poll=False)

        s.run.reset_mock()
        d.runOnce(poll=True)
        s.run.assert_called_once_with(poll=True)
        d.stop = True
        self.assertRaises(SystemExit, d.runOnce)
        d.stop = False
        d.restart = True
        self.assertRaises(SystemExit, d.runOnce)

        s.run.reset_mock()
        d.restart = False
        s.run.side_effect = lambda **x: [][1]
        d.report = mock.Mock()
        d.runOnce()
        d.report.assert_called_once_with()

    @mock.patch('smtplib.SMTP')
    @mock.patch('bigitr.bigitrdaemon.Daemon.createContext')
    def test_report(self, cC, S):
        d = bigitrdaemon.Daemon('/foo', self.daemonConfig, False, self.pidFile)
        try:
            [][1]
        except:
            d.report()
        conn = S().sendmail
        conn.assert_called_once_with(
            'sender@here', ['other@other', 'blah@blah'], mock.ANY)
        msg = conn.call_args[0][2]
        self.assertTrue('\nIndexError: list index out of range\n' in msg)

    @mock.patch('traceback.format_exception')
    @mock.patch('bigitr.bigitrdaemon.Daemon.createContext')
    def test_reportNoEmail(self, cC, t):
        cfg = file(self.daemonConfig).read()
        cfg = cfg.replace('email = other@other blah@blah\n', '')
        file(self.daemonConfig, 'w').write(cfg)
        d = bigitrdaemon.Daemon('/foo', self.daemonConfig, False, self.pidFile)
        d.report()
        t.assert_not_called()

    @mock.patch('traceback.format_exception')
    @mock.patch('bigitr.bigitrdaemon.Daemon.createContext')
    def test_reportNoMailFrom(self, cC, t):
        cfg = file(self.daemonConfig).read()
        cfg = cfg.replace('mailfrom = sender@here\n', '')
        file(self.daemonConfig, 'w').write(cfg)
        d = bigitrdaemon.Daemon('/foo', self.daemonConfig, False, self.pidFile)
        d.report()
        t.assert_not_called()

    @mock.patch('os.execl')
    @mock.patch('time.time')
    @mock.patch('time.sleep')
    @mock.patch('bigitr.bigitrdaemon.Daemon.__init__')
    @mock.patch('bigitr.bigitrdaemon.Daemon.runOnce')
    def test_mainLoop(self, rO, I, sleep, Time, execl):
        I.return_value = None
        d = bigitrdaemon.Daemon()
        d.i = 0
        def stop(**kw):
            if 2 == d.i:
                d.stop = True
            d.i += 1
        d.runOnce.side_effect = stop
        d.cfg = mock.Mock()
        d.cfg.getFullSyncFrequency.return_value = 10
        d.cfg.getPollFrequency.return_value = 5
        d.stop = False
        d.restart = False
        d.context = mock.Mock()
        d.context.detach_process = False
        # first sync is full.  It is shorter than syncfrequency, so the
        # second sync is a poll.  It takes just long enough to exceed the
        # total sync time since last sync, so the
        # third sync is full
        Time.side_effect = [0.1, 1.1,
                            1.2, 10.3,
                            10.4, 10.5]
        self.assertRaises(SystemExit, d.mainLoop)
        d.runOnce.assert_has_calls([mock.call(poll=False),
                                    mock.call(poll=True),
                                    mock.call(poll=False)])
        sleep.assert_called_once_with(4.0)
        execl.assert_not_called()

    @mock.patch('os.execl')
    @mock.patch('time.sleep')
    @mock.patch('bigitr.bigitrdaemon.Daemon.__init__')
    @mock.patch('bigitr.bigitrdaemon.Daemon.runOnce')
    def test_mainLoopSignalHandling(self, rO, I, sleep, execl):
        I.return_value = None
        d = bigitrdaemon.Daemon()
        d.cfg = mock.Mock()
        d.cfg.getFullSyncFrequency.return_value = 1000
        d.cfg.getPollFrequency.return_value = 10000
        d.context = mock.Mock()
        d.context.detach_process = False
        d.stop = False
        d.restart = True
        d.execPath = '/foo'
        d.config = 'b'
        d.pidfile = 'b-p'
        self.assertRaises(SystemExit, d.mainLoop)
        execl.assert_called_once_with('/foo', ['/foo', '--config', 'b', '--pid-file', 'b-p', '--no-daemon'])

        execl.reset_mock()
        d.restart = False
        d.stop = True
        self.assertRaises(SystemExit, d.mainLoop)
        execl.assert_not_called()

@mock.patch('bigitr.bigitrdaemon.Daemon')
class TestMain(testutils.TestCase):
    def test_emptyArgs(self, D):
        bigitrdaemon.main(['/foo'])
        D.assert_called_once_with(
            '/foo', '~/.bigitrd', True, '~/.bigitrd-pid')
        D().run.assert_called_once_with()

    def test_emptyArgsWithEnvironment(self, D):
        os.environ['BIGITR_DAEMON_CONFIG'] = '/b'
        os.environ['BIGITR_DAEMON_PIDFILE'] = '/b-p'
        try:
            bigitrdaemon.main(['/foo'])
            D.assert_called_once_with('/foo', '/b', True, '/b-p')
            D().run.assert_called_once_with()

        finally:
            os.unsetenv('BIGITR_DAEMON_CONFIG')
            os.unsetenv('BIGITR_DAEMON_PIDFILE')

    @staticmethod
    def assertNonDefaultArgs(D):
        D.assert_called_once_with('/foo', '/b', False, '/b-p')
        D().run.assert_called_once_with()

    def test_Args(self, D):
        bigitrdaemon.main(['/foo', '--config', '/b', '--nodaemon', '--pidfile', '/b-p'])
        self.assertNonDefaultArgs(D)

    def test_ArgsShort(self, D):
        bigitrdaemon.main(['/foo', '-c', '/b', '-n', '-p', '/b-p'])
        self.assertNonDefaultArgs(D)

    def test_ArgsLong(self, D):
        bigitrdaemon.main(['/foo', '--config', '/b', '--no-daemon', '--pid-file', '/b-p'])
        self.assertNonDefaultArgs(D)
