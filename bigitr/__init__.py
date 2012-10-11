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
import os
import sys

from bigitr import context
from bigitr import cvsimport
from bigitr import git
from bigitr import gitexport
from bigitr import gitmerge
from bigitr import shell
from bigitr import sync
from bigitr import util

class _Runner(object):
    def __init__(self, appconfig, config, repos):
        self.appconfig = appconfig
        self.config = config
        self.repos = repos
        self.ctx = self.getContext()
        self._init_runner()

    def getContext(self):
        appconfig = self.expandFilenameIfString(self.appconfig)
        config = self.expandFilenameIfString(self.config)
        return context.Context(appconfig, config)

    def _init_runner(self):
        raise NotImplementedError

    def expandFilenameIfString(self, stringish):
        if isinstance(stringish, str):
            return util.fileName(stringish)
        return stringish

    def getBranchMaps(self):
        repolist = self.repos
        if not repolist:
            repolist = self.ctx.getRepositories()

        try:
            branchMap = [x.rsplit('::', 1) for x in repolist]
            branchMap = [l + [None] if len(l) == 1 else l for l in branchMap]
            return [[self.ctx.getRepositoryByName(x), y] for x, y in branchMap]
        except KeyError, e:
            raise KeyError('repository %s not found' %e.args[0])

    def process(self):
        for repository, branch in self.getBranchMaps():
            Git = git.Git(self.ctx, repository)
            try:
                if not branch:
                    # empty branch is unspecified
                    branch = None
                self.do(repository, Git, requestedBranch=branch)
            except shell.ErrorExitCode, e:
                # report errors from commands that fail
                Git.log.mailLastOutput(str(e))
                self.runner.err.report(repository)
            except:
                self.runner.err.report(repository)

    def close(self):
        for l in self.ctx.logs.values():
            l.close()

    def run(self):
        self.process()
        self.close()

class Synchronize(_Runner):
    def __init__(self, appconfig, config, repos, poll=False):
        _Runner.__init__(self, appconfig, config, repos)
        self.poll = poll

    def run(self, poll=None):
        if poll is not None:
            self.poll = poll
        _Runner.run(self)

    def do(self, repo, Git, requestedBranch=None):
        # Synchronize ignores branch specifications
        if self.poll:
            if not self.newContent(Git):
                return
        self.runner.synchronize(repo, Git)

    def newContent(self, Git):
        if not os.path.exists(Git.path):
            return True
        oldRefs = Git.refs()
        Git.fetch
        if Git.refs() == oldRefs:
            return False
        return True

    def _init_runner(self, *args):
        self.runner = sync.Synchronizer(self.ctx)

class Import(_Runner):
    def _init_runner(self, *args):
        self.runner = cvsimport.Importer(self.ctx)
        self.do = self.runner.importBranches

class Export(_Runner):
    def _init_runner(self, *args):
        self.runner = gitexport.Exporter(self.ctx)
        self.do = self.runner.exportBranches

class Merge(_Runner):
    def _init_runner(self, *args):
        self.runner = gitmerge.Merger(self.ctx)
        self.do = self.runner.mergeBranches


def main(argv):
    appConfigName = os.environ.get('BIGITR_APP_CONFIG', '~/.bigitr')
    repoConfigName = os.environ.get('BIGITR_REPO_CONFIG', '~/.bigitr-repository')
    ap = argparse.ArgumentParser(description='Synchronize Git and CVS')
    ap.add_argument('subcommand', help='sync|import|export|merge|help')
    ap.add_argument('--appconfig', '-a', default=appConfigName,
                    help='bigitr configuration file [%s]' %appConfigName)
    ap.add_argument('--config', '-c', default=repoConfigName,
                    help='repository configuration file [%s]' %repoConfigName)
    ap.add_argument('repository', action='append', nargs='*',
                    help='repositories to process [all configured repositories]')
    args = ap.parse_args(argv)

    if args.subcommand == 'help':
        ap.print_help()
        raise SystemExit(0)
    elif args.subcommand == 'sync':
        raise SystemExit(Synchronize(args.appconfig, args.config, args.repository[0]).run())
    elif args.subcommand == 'import':
        raise SystemExit(Import(args.appconfig, args.config, args.repository[0]).run())
    elif args.subcommand == 'export':
        raise SystemExit(Export(args.appconfig, args.config, args.repository[0]).run())
    elif args.subcommand == 'merge':
        raise SystemExit(Merge(args.appconfig, args.config, args.repository[0]).run())

    # unrecognized subcommand
    ap.print_help()
    raise SystemExit(1)
