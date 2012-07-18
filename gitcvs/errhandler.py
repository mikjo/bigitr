import sys
import traceback

import appconfig
import log

class Errors(object):
    def __init__(self, ctx):
        self.ctx = ctx

    def __call__(self, repo, action):
        exception = sys.exc_info()
        self.report(repo, exception, action)
        if action == appconfig.ABORT:
            raise exception[0], exception[1], exception[2]

    def report(self, repo, exception=None, action=appconfig.WARN):
        if exception is None:
            exception = sys.exc_info()
        # log error in all cases, no matter what
        errmsg = ("Error for repository '%s':\n" %repo) + ''.join(
            traceback.format_exception(*exception))
        self.ctx.logs[repo].writeError(errmsg)

        if action == appconfig.WARN:
            # also print error to stderr; ABORT will end up on
            # stderr anyway at a higher level so do not duplicate
            sys.stderr.write(errmsg)
            sys.stderr.flush()
