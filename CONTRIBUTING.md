Contributing to Bigitr
======================

Reporting bugs is a contribution.  Please report bugs using the
github issue tracker at https://github.com/mikjo/bigitr/issues


Understanding the Code
----------------------

### Software ###

The `bigitr` directory contains the python module that implements
all the application logic.

* `__init__.py`: Application `main()` and supporting classes.

* `config.py`: `Config` base class inherited by all classes
  that implement bigitr configuration.

* `appconfig.py`: `AppConfig` parser for bigitr application
  configuration named by the `BIGITR_APP_CONFIG` environment
  variable, or `~/.bigitr` by default.

* `repositorymap.py`: `RepositoryConfig` parser for repository
  configuration that *maps* Git *repositories* to CVS locations.

* `context.py`: `Context` multiplex pseudo-mixin of `AppConfig` and
  `RepositoryConfig` to implement configuration functionality that
  depends on both application and repository configuration, and to
  present a unified configuration interface to consumers without
  having to know where any particular configuration item comes from.
  Also holds caches of configuration-sensitive cacheables.

* `daemonconfig.py`: `DaemonConfig` parser for bigitrd daemon
  configuration named by the `BIGITR_DAEMON_CONFIG` environment
  variable, or `~/.bigitrd` by default.

* `bigitrdaemon.py`: Bigitr daemon `main()` implementation and
  supporting classes.

* `cvsimport.py`: `Importer` class contains the business logic
  for the process of importing content from CVS onto branches
  in Git. Instantiates `Merger` to process any merges on Git
  branches as a result of the import operation.

* `cvs.py`: `CVS` class implementing low-level methods for actions
  in CVS checkouts and creating CVS exports; mostly invocations of
  the `cvs` command, and running user-supplied hooks in the CVS
  checkout. Used by both `Importer` and `Exporter`.

* `gitexport.py`: `Exporter` class contains the business logic
  for the process of exporting content from Git onto branches
  in CVS.

* `gitmerge.py`: `Merger` class contains the business logic for
  the process of merging Git branches into other Git branches,
  including cascaded triggered merges.

* `git.py`: `Git` class implementing low-level methods for actions
  in Git repository clones; mostly invocations of the `git` command,
  and running user-supplied hooks in the Git repository clone.
  Used by `Importer`, `Exporter`, and `Merger`.

* `errhandler.py`: `Errors` class implementing applying configuration to
  error handling, including logging and creating (but not sending)
  email messages about errors, as configured.

* `log.py`: `Log` class implementing logging each business action to
  a separate, timestamped and timelogged file for each of standard
  output and standard error, and actions taken on log files such as
  compression and mailing finished logs. Also, `LogCache` class caches
  `Log` objects.

* `mail.py`: `Email` class implementing email message definition and
  sending via SMTP, as configured. Also, `MailCache` class caches
  `Email` objects.

* `progress.py`: `Progress` class to provide terminal progress (in
  the command line `bigitr` case) and "proctitle" information via
  the `Proctitle` class in both the command line and daemond `bigitrd`
  cases.

* `shell.py`: `LoggingShell` class to issue shell commands and log
  their output so that the standard and error output can be separately
  provided in error messages and investigated forensically even if
  no errors have been raised.

* `sync.py`: `Synchronizer` class invokes the `Importer` and
  `Exporter` classes to fully and automatically synchronize a
  single Git repository with its corresponding CVS location, in
  both directions if so configured, including all configured branch
  merges.

* `util.py`: Utility methods and decorators used throughout.

The `bin` directory contains the python script `bigitr` that
implements the command-line interface, including running from a
checkout even if `PYTHONPATH` is not set to include the checkout.

The `sbin` directory contains the python script `bigitrd` that
implements the daemon, including running from a checkout even if
`PYTHONPATH` is not set to include the checkout.

The `libexec` directory contains scripts that may be run as hooks
from within a particular bigitr configuration.

### Tests ###

The `unit_test` directory contains unit tests and functional tests.
These tests should run quickly (within about a second) in order to
make it trivial and fast to "smoke-test" all of the bigitr module
after any change.  Each module in the `bigitr` directory has a
corresponding modules in the `unit_test` directory.  In general,
when adding new tests, it is reasonable for them to be functional
with respect to depending on real configuration objects, but should
have reasonably limited dependencies between modules otherwise,
to avoid unnecessarily limiting refactoring.

The `testdata` directory contains a base file with Git and CVS
content that is the initial input for the story tests.  The story
tests cache their changes between tests in transient files also
stored in the `testdata` directory, but which are ignored by the
`.gitignore` file and must not be committed to the Git repositories.

The `story_test` directory contains a single large module. It has
a `TestStoryAPI` class that runs stories that prove the business
logic of export, import, merge, and full synchronization, using the
programs (like CVS and Git) installed on the system and on which
Bigitr explicitly depends.  Modifications that change the business
logic of any of these processes should have falsifying tests or
test modifications included.  The `bigitr` and `bigitrd` scripts
are also tested in the `TestStoryCommands` class.  The classes and
methods are named so that they will sort in an order that will cause
the cacheing of the repository state between tests to progress in
the correct order, so that after the states are cached, individual
tests can be run during new development.

All the unit tests are invoked with `make unit`, all the story tests
are invoked with `make story`, the unit and story tests are serially
but separately invoked with `make tests`, and all the tests are invoked
together with `make alltests`.

The story tests cannot be run individually until after they are run
sequentially.  The file testdata/TESTROOT.1.tar.gz is included in
the repository to bootstrap the process, and other TESTROOT files
in testdata (required for subsequent story tests) are generated
when the story tests are run.  The .gitignore file ignores all
changes; the TESTROOT.1.tar.gz file should not be changed, and
the other files should never be committed to the Git repository.
If you have a major update to Git or CVS and tests fail, or if
you experience failing tests the first time you run the test suite
(when the cache files are initially generated), you should delete
the cached TESTROOT files by running `make testclean`.


Contributing Code to Bigitr
---------------------------

For contributing modifications, the following description describes
the policy which will be used for evaluating and possibly accepting
the modifications.  It does not supersede any terms of the license.

If you make modifications, you may offer those modifications
to be included bigitr by using a "pull request" in Github.  All
contributions must be under the terms and conditions of the Apache
License; contributions offered otherwise will not be accepted.

In order to avoid merge failures, we request that your "prominent
notices stating that You changed the files" as required by the
Apache License be in the form of correct and complete name and correct
email address in the `Author` field of the Git commits that you
submit, rather than changes to the *contents* of the files that you
modify.  You may, of course, add appropriate copyright statements.

Contributions which include modifications to the source code are
requested to include appropriate tests for the changes.  New or
modified tests should cover all of the changed and affected code,
maintaining 100% unit test code coverage as well as 100% coverage
of normal logic in story tests.  To make sure that story tests work
correctly both with and without cached testdata, please purge the
cache and run all tests twice; once without cached testdata and
once with cached testdata:
    make testclean
    make alltests
    make alltests

Bigitr must function correctly on Python 2.6, and is expected also
to function correctly on Python 2.7.


License
=======

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Copyright 2012-2013 SAS Institute
