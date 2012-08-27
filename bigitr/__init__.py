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
from bigitr import sync

class _Runner(object):
    def __init__(self, args):
        self.args = args
        self.repos = args.repository[0]
        self.ctx = self.getContext()

    def getContext(self):
        return context.Context(self.fileName(self.args.appconfig),
                               self.fileName(self.args.config))

    def fileName(self, name):
        return os.path.abspath(os.path.expandvars(os.path.expanduser(name)))

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

    def run(self):
        raise NotImplementedError

    def process(self, c, f):
        for repository, branch in self.getBranchMaps():
            Git = git.Git(self.ctx, repository)
            try:
                if not branch:
                    # empty branch is unspecified
                    branch = None
                f(repository, Git, requestedBranch=branch)
            except:
                c.err.report(repository)

    def close(self):
        for l in self.ctx.logs.values():
            l.close()

class Synchronize(_Runner):
    def run(self):
        s = sync.Synchronizer(self.ctx)
        # Synchronize ignores branch specifications
        self.process(s, lambda x, y, **z: s.synchronize(x, y))
        self.close()

class Import(_Runner):
    def run(self):
        i = cvsimport.Importer(self.ctx)
        self.process(i, i.importBranches)
        self.close()

class Export(_Runner):
    def run(self):
        e = gitexport.Exporter(self.ctx)
        self.process(e, e.exportBranches)
        self.close()

class Merge(_Runner):
    def run(self):
        m = gitmerge.Merger(self.ctx)
        self.process(m, m.mergeBranches)
        self.close()


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
        raise SystemExit(Synchronize(args).run())
    elif args.subcommand == 'import':
        raise SystemExit(Import(args).run())
    elif args.subcommand == 'export':
        raise SystemExit(Export(args).run())
    elif args.subcommand == 'merge':
        raise SystemExit(Merge(args).run())

    # unrecognized subcommand
    ap.print_help()
    raise SystemExit(1)
