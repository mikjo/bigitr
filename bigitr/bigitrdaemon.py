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

import argparse
import daemon
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import lockfile
import os
import signal
import smtplib
import sys
import time
import traceback

from bigitr import appconfig
from bigitr import daemonconfig
from bigitr import progress
from bigitr import repositorymap
from bigitr import Synchronize
from bigitr import util

class Daemon(object):
    def __init__(self, execPath, config, detach, pidfile):
        self.execPath = execPath
        self.config = util.fileName(config)
        self.cfg = daemonconfig.DaemonConfig(config)
        self.pidfile = util.fileName(pidfile)
        self.restart = False
        self.stop = False
        if detach:
            self.progress = progress.Progress(outFile=None)
        else:
            self.progress = progress.Progress()
        self.createContext(detach)
        self.createSynchronizers()

    def createContext(self, detach):
        self.context = daemon.DaemonContext()
        self.context.pidfile = lockfile.FileLock(self.pidfile)
        self.context.detach_process = detach
        if not detach:
            self.context.stdout = sys.stdout
            self.context.stderr = sys.stderr
        self.context.working_directory = os.getcwd()
        # umask cannot be queried without being set
        u = os.umask(0)
        os.umask(u)
        self.context.umask = u
        self.context.signal_map[signal.SIGHUP] = self.sighup
        self.context.signal_map[signal.SIGTERM] = self.sigterm
        self.context.signal_map[signal.SIGINT] = self.sigterm
        self.context.signal_map[signal.SIGCHLD] = self.sigchld

    def createSynchronizers(self):
        self.synchronizers = []
        addMail = None
        if self.cfg.getMailAll():
            addMail = self.cfg.getEmail()
        for appCtxName in self.cfg.getApplicationContexts():
            appCtx = self.cfg.getAppConfig(appCtxName)
            appCtx = appconfig.AppConfig(appCtx)
            for repoCtx in self.cfg.getRepoConfigs(appCtxName):
                repoCtx = repositorymap.RepositoryConfig(repoCtx)
                for repo in repoCtx.getRepositories():
                    repoCtx.addEmail(repo, addMail)
                    self.synchronizers.append(
                        Synchronize(appCtx, repoCtx, [repo]))

    def run(self):
        try:
            self.context.pidfile.acquire(timeout=0.1)
        except (lockfile.AlreadyLocked, lockfile.LockTimeout):
            lockpid = None
            if os.path.exists(self.pidfile):
                lockpid = int(file(self.pidfile).read().strip())
            if (lockpid and lockpid != os.getpid() and util.kill(lockpid, 0)):
                raise lockfile.AlreadyLocked, 'Process %d has %s locked' %(
                    lockpid, self.pidfile)
            self.context.pidfile.break_lock()
        try:
            with self.context:
                file(self.pidfile, 'w').write(str(os.getpid()))
                self.mainLoop()
        finally:
            if self.context.pidfile.is_locked():
                self.context.pidfile.release()
            if os.path.exists(self.pidfile):
                os.remove(self.pidfile)

    def sigterm(self, signo, frame):
        'stop after all child processes have finished'
        self.stop = True

    def sighup(self, signo, frame):
        'reload by re-execing when all child processes have finished'
        self.restart = True

    def sigchld(self, signo, frame):
        pass

    def runOnce(self, poll=False):
        if poll:
            self.progress.setPhase('poll')
        else:
            self.progress.setPhase('sync')
        for s in self.synchronizers:
            if not self.stop and not self.restart:
                try:
                    repoName = s.ctx.getRepositoryName(s.repos[0])
                    self.progress.add(repoName)
                    self.progress.report()
                    s.run(poll=poll)
                    self.progress.remove(repoName)
                except:
                    self.report()
            else:
                raise SystemExit(0)

    def report(self):
        exception = sys.exc_info()
        email = self.cfg.getEmail()
        if not email:
            return
        mailfrom = self.cfg.getMailFrom()
        if not mailfrom:
            return

        msgText = traceback.format_exception(*exception)

        msg = MIMEMultipart()
        msg['Subject'] = 'bigitrd error report'
        msg['From'] = mailfrom
        msg['To'] = ', '.join(email)
        msg.preamble = 'Bigitrd traceback'
        tbmsg = MIMEText(''.join(msgText))
        tbmsg.add_header('Content-Disposition', 'inline')
        msg.attach(tbmsg)
        s = smtplib.SMTP(self.cfg.getSmartHost())
        s.sendmail(mailfrom, email, msg.as_string())
        s.quit()


    def mainLoop(self):
        # FUTURE: implement self.cfg.parallelConversions() parallelization
        syncFreq = self.cfg.getFullSyncFrequency()
        pollFreq = self.cfg.getPollFrequency()
        waitTime = 0
        syncTime = 0
        poll=False
        try:
            while not self.stop and not self.restart:
                if waitTime > 0:
                    self.progress.clear()
                    self.progress.setPhase('sleep')
                    self.progress.add('%0.1f seconds' %waitTime)
                    self.progress.report()
                    time.sleep(waitTime)
                    self.progress.clear()
                startTime = time.time()
                if not poll:
                    syncStartTime = startTime

                self.runOnce(poll=poll)

                now = time.time()
                duration = now-startTime
                syncDuration = now-syncStartTime
                syncTime = max(0, syncFreq - syncDuration)
                pollTime = max(0, pollFreq - duration)
                poll = (pollTime < syncTime)
                waitTime = min(syncTime, pollTime)

        finally:
            if self.restart:
                execArgs = [self.execPath,
                            '--config', self.config,
                            '--pid-file', self.pidfile]
                if not self.context.detach_process:
                    execArgs.append('--no-daemon')
                os.execl(self.execPath, *execArgs)

        raise SystemExit(0)


def main(argv):
    daemonConfig = os.environ.get('BIGITR_DAEMON_CONFIG', '~/.bigitrd')
    daemonPidFile = os.environ.get('BIGITR_DAEMON_PIDFILE', '~/.bigitrd-pid')
    ap = argparse.ArgumentParser(description='Daemon to synchronize Git and CVS')
    ap.add_argument('--config', '-c', default=daemonConfig,
                    help='daemon configuration file [%s]' %daemonConfig)
    ap.add_argument('--nodaemon', '--no-daemon', '-n', action='store_true',
                    help='run in the foreground')
    ap.add_argument('--pidfile', '--pid-file', '-p', default=daemonPidFile,
                    help='daemon pid file path [%s]' %daemonPidFile)

    args = ap.parse_args(argv[1:])

    Daemon(argv[0], args.config, not args.nodaemon, args.pidfile).run()
