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

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import weakref

def ifEmail(fn):
    def wrapper(self, *args, **kwargs):
        if self.ignore is True:
            return
        fn(self, *args, **kwargs)
    return wrapper


class Email(object):
    def __init__(self, ctx, repo, cache):
        self.recipients = ctx.getEmail(repo)
        self.mailfrom = ctx.getMailFrom()
        self.ignore = False
        if self.recipients is None or self.mailfrom is None:
            self.ignore = True
            return

        self.ctx = ctx
        self.cache = None
        if cache is not None:
            self.cache = weakref.ref(cache)
        self.repo = repo
        self.msg = MIMEMultipart()
        self.msg['Subject'] = '%s: bigitr error report' % repo
        self.msg['From'] = self.mailfrom
        self.msg['To'] = ', '.join(self.recipients)
        self.msg.preamble = 'Bigitr error report for repository %s' % repo

    @staticmethod
    def _filename(desc):
        desc = '_'.join(x for x in desc.split())
        desc = ''.join(x for x in desc if x.isalnum() or x == '_')
        return desc + '.txt'

    @ifEmail
    def addAttachment(self, text, desc):
        msg = MIMEText(text)
        msg.add_header('Content-Disposition', 'attachment',
                       filename=self._filename(desc))
        self.msg.attach(msg)

    @ifEmail
    def addOutput(self, command, stdout, stderr):
        self.addAttachment(stderr, 'errors from ' + command)
        self.addAttachment(stdout, 'output from ' + command)

    @ifEmail
    def send(self, allout, allerr):
        # send email only if an error has been attached
        if self.msg.get_payload():
            # First, attach the entire repository log; the individual
            # command messages will be embedded in it
            self.addAttachment(allerr, 'all errors')
            self.addAttachment(allout, 'all output')
            self._send()
        if self.cache and self.cache():
            del self.cache()[self.repo]

    def _send(self):
        s = smtplib.SMTP(self.ctx.getSmartHost())
        s.sendmail(self.ctx.getMailFrom(),
                   self.recipients, self.msg.as_string())
        s.quit()

class MailCache(dict):
    def __init__(self, ctx):
        self.ctx = ctx

    def __getitem__(self, name):
        if not self.has_key(name):
            self.__setitem__(name, Email(self.ctx, name, self))
        return dict.__getitem__(self, name)
