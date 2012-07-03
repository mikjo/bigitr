import logging
import os
import subprocess
import time

class LoggingShell(subprocess.Popen):
    def __init__(self, log, *args, **kwargs):
        self.log = log
        self.error = kwargs.pop('error', True)
        kwargs.setdefault('stderr', log.stderr)
        kwargs.setdefault('stdout', log.stdout)
        ts = self.timestamp()
        cmd = ' '.join(args)
        start = ' '.join((ts, 'START:', cmd, '\n'))
        os.write(log.stderr, start)
        os.write(log.stdout, start)
        self.log.markStart()
        self.p = subprocess.Popen.__init__(self, args, **kwargs)

    def timestamp(self):
        now = time.time()
        frac = '%4.4f' %(now - int(now))
        loc = time.localtime
        tzname = time.tzname[time.daylight]
        return time.strftime('[%a %b %d %H:%m:%S.'
                             + frac[2:] + ' ' + tzname + ' %Y]')

    def finish(self):
        retcode = subprocess.Popen.wait(self)
        self.log.markStop()
        ts = self.timestamp()
        finish = '%s COMPLETE with return code: %d\n' %(ts, retcode)
        os.write(self.log.stderr, finish)
        os.write(self.log.stdout, finish)
        if retcode and self.error:
            for line in open(self.log.thiserr):
                logging.error(line)
            logging.error(self.log.thiserr)
            raise ValueError('Unexpected return code %d' %retcode)
        return retcode

def run(log, *args, **kwargs):
    s = LoggingShell(log, *args, **kwargs)
    return s.finish()

def read(log, *args, **kwargs):
    kwargs['stdout'] = subprocess.PIPE
    s = LoggingShell(log, *args, **kwargs)
    output = s.communicate()
    retcode = s.finish()
    return retcode, output[0]
