import logging
import os
import subprocess

class LoggingShell(subprocess.Popen):
    def __init__(self, log, *args, **kwargs):
        self.log = log
        self.error = kwargs.pop('error', True)
        kwargs.setdefault('stderr', log.stderr)
        kwargs.setdefault('stdout', log.stdout)
        self.p = subprocess.Popen.__init__(self, args, **kwargs)

    def wait(self):
        retcode = subprocess.Popen.wait(self)
        if retcode:
            os.write(self.log.stderr,
                     'command returned exit code %d\n' %retcode)
            logging.error(self.log.thiserr)
            for line in open(self.log.thiserr):
                logging.error(line)
            if self.error:
                raise ValueError('Unexpected return code %d' %retcode)
        return retcode

def run(log, *args, **kwargs):
    s = LoggingShell(log, *args, **kwargs)
    return s.wait()

def read(log, *args, **kwargs):
    kwargs['stdout'] = subprocess.PIPE
    s = LoggingShell(log, *args, **kwargs)
    output = s.communicate()
    retcode = s.wait()
    return retcode, output[0]
