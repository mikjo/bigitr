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
import setproctitle
import sys

import testutils

from bigitr import progress


class TestProctitle(testutils.TestCase):
    def test_lifecycle(self):
        t = setproctitle.getproctitle()
        try:
            p = progress.Proctitle()
            self.assertEqual(t, setproctitle.getproctitle())
            p('')
            self.assertEqual('bigitrd ', setproctitle.getproctitle())
            p('foo')
            self.assertEqual('bigitrd foo', setproctitle.getproctitle())
        finally:
            del p
            self.assertEqual(t, setproctitle.getproctitle())

class TestProgress(testutils.TestCase):
    @mock.patch('bigitr.progress.Proctitle')
    def test_stdout(self, P):
        p = progress.Progress()
        # sys.stdout in declaration evaluated before nose changes it
        self.assertEquals(p.outFile, sys.modules['sys'].stdout)

    @mock.patch('bigitr.progress.Proctitle')
    def test_proctitleProgress(self, P):
        p = progress.Progress(outFile=None)
        p.outFile = P()
        p.report()
        P().assert_called_once_with(': ')

    def lifecycle(self, P, outFile):
        p = progress.Progress(outFile=outFile)
        p.report()
        if outFile is not None:
            outFile.write.assert_called_once_with('\r\r: \r')
            outFile.flush.assert_called_once_with()
            outFile.reset_mock()
        P().assert_called_once_with(': ')
        P().reset_mock()
        p.setPhase('one')
        p.report()
        if outFile is not None:
            outFile.write.assert_called_once_with('\r  \rone: \r')
            outFile.flush.assert_called_once_with()
            outFile.reset_mock()
        P().assert_called_once_with('one: ')
        P().reset_mock()
        p.add('b')
        p.report()
        if outFile is not None:
            outFile.write.assert_called_once_with('\r     \rone: b\r')
            outFile.flush.assert_called_once_with()
            outFile.reset_mock()
        P().assert_called_once_with('one: b')
        P().reset_mock()
        p.add('a')
        p.report()
        if outFile is not None:
            outFile.write.assert_called_once_with('\r      \rone: a b\r')
            outFile.flush.assert_called_once_with()
            outFile.reset_mock()
        P().assert_called_once_with('one: a b')
        P().reset_mock()
        p.remove('b')
        p.report()
        if outFile is not None:
            outFile.write.assert_called_once_with('\r        \rone: a\r')
            outFile.flush.assert_called_once_with()
            outFile.reset_mock()
        P().assert_called_once_with('one: a')
        P().reset_mock()
        p.setPhase('two')
        p.report()
        if outFile is not None:
            outFile.write.assert_called_once_with('\r      \rtwo: a\r')
            outFile.flush.assert_called_once_with()
            outFile.reset_mock()
        P().assert_called_once_with('two: a')
        P().reset_mock()
        p.clear()
        p.report()
        if outFile is not None:
            outFile.write.assert_called_once_with('\r      \rtwo: \r')
            outFile.flush.assert_called_once_with()
            outFile.reset_mock()
        P().assert_called_once_with('two: ')
        P().reset_mock()
        del p
        if outFile is not None:
            outFile.write.assert_called_once_with('\r     \r')
            outFile.flush.assert_called_once_with()
        P().assert_called_once_with('idle')

    @mock.patch('bigitr.progress.Proctitle')
    def test_lifecycleNoDaemon(self, P):
        o = mock.Mock()
        self.lifecycle(P, outFile=o)

    @mock.patch('bigitr.progress.Proctitle')
    def test_lifecycleDaemon(self, P):
        self.lifecycle(P, outFile=None)
