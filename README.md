Bigitr
======

Bigitr is a tool that copies content bidirectionally between Git
and CVS repositories in an asynchronous and asymmetric fashion.
The name *Bigitr* is intended to convey at least bidirectionality,
an emphasis on Git over CVS, and that it helps to *beget* Git
repositories from CVS repositories.

Unlike Git's cvsimport, Bigitr does not attempt to assemble
changesets out of CVS into separate Git commits.  It merely takes
snapshots of the current (at the time of the snapshot) state of CVS,
using the `cvs export` command.  Similarly, it does not export Git
commits separately into CVS; it writes only the current (at the time)
latest content from the specified Git branch into CVS.

The flow is conceptually similar to Git's flow for synchronizing
with a remote repository.  For example, in Git, the local `master`
branch is pushed to the `master` branch on the `origin` repository,
pulled from the `origin` remote's `master` branch to the local
`origin/master` reference, and then the local `origin/master`
reference is merged onto the local `master` branch.  Similarly, in
Bigitr, the Git `master` branch might be exported to a CVS branch
named `current-dev`, which is then imported into a Git branch named
`cvs-current-dev`, which then might be merged back into the Git
`master` branch.

The bidirectional synchronization is not intended to allow developers
to develop in their choice of CVS or Git indefinitely.  Bigitr should
be used in order to move primary development of a branch from CVS
to Git.  After that, the purpose of merging changes from CVS into Git
is to preserve the content of changes that have to be made in CVS,
without preserving context (changeset or commit messages).

Bigitr is a power tool, and like all power tools, it is dangerous.
It commits to CVS and pushes to remote Git repositories.
Wrong configuration or bugs in Bigitr can be very destructive to
your source code, both in CVS and in Git.  Do backups, and test
configuration initially with throwaway copies of CVS and Git
repositories, before you put this tool into production use.


Reserved Branch Names
---------------------

Branches in the Git repositories with names starting with `cvs-`
and `export-` are reserved to be written only by Bigitr.
These branches are pushed to the origin repository so that local
state does not need to be maintained.  This means that multiple
users can run this tool using the same repository configuration
but different application configuration (local directories).
However, no locking is attempted, so if two users run it at the
same time, the results are undefined.


Bigitr imports branches from CVS into special import branches (with
names starting with "cvs-") in Git.  It also exports branches in
Git into branches in CVS.  It will not touch the CVS trunk (at
least at this time).

Note: It will not synchronize only parts of a CVS `sub/module`.  It is
all or nothing: for any particular `sub/module`, any files not in
the Git branch being exported to CVS will be **deleted** from that
branch in that CVS `sub/module`.

It records which content has been pushed from a Git branch into
CVS by using another branch on the origin with a name that
starts with `export-`.  If you export the Git `master` branch
to CVS, Bigitr will track what has been exported using the
`export-master` branch.  It uses this to attach Git commit
messages to CVS commits.  It makes no attempt to attach CVS
commit messages to Git commits.


Merging
-------

After committing to branches (not including fast-forwarding the
export- branches), Bigitr will automatically attempt to merge changes
into other explicitly-specified branches.  If any merges are
successful, those merges themselves may trigger other merge
operations.

It is reasonable to configure no automatic merging at all.  Be,
aware that if you have configured the Git "master" branch to be
exported to an existing CVS branch, then you should populate the
Git "master" branch before exporting.

Any branch that you export from Git to CVS, including master,
must be populated before you export it.  You may populated it
by merging from a branch imported from CVS, either manually or
by configuring an automatic merge.

Files in CVS ignored by .gitignore will not be committed to the
corresponding Git branches, and if those .gitignore changes are
represented on a branch being exported from Git into CVS, those
files will be deleted from the CVS branch when the Git branch
is exported to CVS.

Files with names starting with ".git" will not be commited to CVS;
that file namespace is reserved for Git, even for Git metadata file
types that have not yet been created as of the time that this tool
was written.

Bigitr tries to notice entirely empty branches and should refuse to
delete entire CVS `sub/modules`.  An attempt to export an empty Git
branch to a CVS branch will raise an exception rather than deleting
all the files on the CVS branch.  However, even a single file is
enough to override this security check.)  (If you really want to
delete all the files on the CVS branch, do it using CVS directly.)

It is recommended that only Git metadata files with names starting
with .git be included in "skeletons" used to populate empty
branches, because the protections against accidentally exporting
empty branches to CVS apply only to Git metadata files.  Putting
any other files in a skeleton may cause you to delete a CVS
`sub/module` due to misconfiguring a repository in Bigitr.


Hooks
-----

There are pre-commit and post-commit hooks for both Git and CVS,
in order to implement normalization rules, notification, and so
forth.  These commands are run with the current working directory
set to the Git working directory or CVS checkout.  These can be
specified for all repositories or for a single repository, and
for all branches or only individual branches.  Any arguments are
included in the configuration using shell syntax; no extra
arguments are added by Bigitr at run time.


Configuration
-------------

There are two kinds of configuration files.

* Application configuration: general behavior

* Repository configuration: specific to a Git repository

Both of these kinds of configuration files use "ini" syntax.
This is intentionally similar to Git configuration.  Any syntax
differences are due to using the Python ConfigFile parser to
implement the configuration file handling.

These files support using `#` characters for comments.  It is normal
to *comment out* configuration lines that do not currently apply
but might apply later.

The values in these files can include environment variables,
which must be specified using the `${VARNAME}` syntax.

In addition, there are skeleton directories containing initial
files for populating new branches, hooks that are called before
and after commits, and working directories in which CVS and
Git operations are done and log files are stored.

### Application configuration ###

A bigitr.conf file has three sections:

    # Comment
    [global]
    gitdir = /path/to/directory/holding/git/repositories
    logdir = /path/to/log/directory
    mailfrom = sendinguser@host
    smarthost = smtp.smarthost.name

    [import]
    onerror = abort # abort|warn|continue
    resetids = true # false to leave $cvsid:...$ alone
    cvsdir = /path/to/directory/for/cvs/export

    [export]
    preimport = true # false to overwrite whatever is in CVS
    onerror = abort # abort|warn|continue
    cvsdir = /path/to/directory/for/cvs/checkouts

To avoid permissions problems, it is **very strongly** recommended
that none of the directories be shared between different users
running Bigitr. The only reasonable exception is `logdir`, which
may use the *sticky bit* (like `/tmp` typically uses) to allow
all users to log output and errors to the same locations for all
converted repositories.

Typically, all of the directories (except possibly `logdir`) are
subdirectories of a single parent directory.  Also, `logdir` is
the only directory that contains information of potentially durable
value.  When Bigitr is not running, it is not generally harmful
to remove any of the directories; Bigitr will re-create them as
necessary.  The logs are voluminous, and contain errors and output
created while Bigtr is running.  This includes errors and output
from hooks.  The logs will be compressed.  They are intended to
be potentially useful for forensic investigation when things go
wrong.

In order to share configuration between users, it is best to use
environment variables for variable parts of the path.  A typical
configuration might be:

    [global]
    logdir = ${BIGITR_LOG}/log
    gitdir = ${BIGITR_DATA}/git

    [import]
    onerror = abort
    resetids = true
    cvsdir = ${BIGITR_DATA}/export

    [export]
    preimport = true
    onerror = abort
    cvsdir = ${BIGITR_DATA}/import

*   `global.logdir`: This directory contains subdirectories,
    one per repository, with logs of output (one each for standard
    output and standard error) from commands run by Bigitr.
    This is the only work directory that should generally be on
    durable storage, and the only work directory that may (with
    appropriate permissions) be shared among multiple users of
    Bigitr.

*   `global.gitdir`: This contains cloned Git repositories.
    Do not use these for normal development purposes.  Bigitr
    throws away any outstanding work in the working directories,
    so any changes you have made will be destroyed.

*   `import.cvsdir`: This contains per-repository subdirectories
    which Bigitr populates by running `cvs export`.

*   `export.cvsdir`: This contains per-repository, per-branch
    directories which Bigitr populates by running `cvs checkout`.

### Repository configuration ###

A repository.conf file has one section per repository, plus an
optional `GLOBAL` section that is inherited by all the
repository sections in that file.


    [GLOBAL]
    gitroot = git@host # <gitroot>:<repositoryname>
    cvsroot = @servername:/path # pserver:<username> added dynamically
    skeleton = ${BIGITR_CONF}/path/to/general/skeleton

    [Path/To/Git/repository]
    cvspath = Path/To/CVS/directory
    skeleton = ${BIGITR_CONF}/path/to/repository/skeleton
    branchfrom = <gitspec> # branch/tag/ref to branch from for new branch imports
    cvs.<branch> = <gitbranch> # CVS <branch> imports to "cvs-<gitbranch>" in Git
    git.<branch> = <cvsbranch> # Git <branch> exports to "<cvsbranch>" in CVS
    merge.<sourcebranch> = <targetbranch> <targetbranch> # Merge <sourcebranch> onto <targetbranch>(es)
    prefix.<branch> = <message> # prefix for CVS commit messages on <branch>
    email = <address> <address> # errors/warnings emailed to these addresses

    prehook.git = <command> <args> # hook to run in Git clone before committing to either Git or CVS
    prehook.imp.git = <command> <args> # hook to run in Git clone before committing to Git from CVS
    prehook.exp.git = <command> <args> # hook to run in Git clone before committing to CVS from Git
    prehook.cvs = <command> <args> # hook to run in CVS checkout before committing to CVS

    posthook.git = <command> <args> # hook to run in Git clone after committing to either Git or CVS
    posthook.imp.git = <command> <args> # hook to run in Git clone after committing to Git from CVS
    posthook.exp.git = <command> <args> # hook to run in Git clone after committing to CVS from Git
    posthook.cvs = <command> <args> # hook to run in CVS checkout after committing to CVS

    prehook.git.<branch> = <command> <args> # hook to run in Git clone before committing to Git branch <branch> or exporting it to CVS
    prehook.imp.git.<branch> = <command> <args> # hook to run in Git clone before committing to Git branch <branch> from CVS
    prehook.exp.git.<branch> = <command> <args> # hook to run in Git clone before committing to CVS from Git branch <branch>
    prehook.cvs.<branch> = <command> <args> # hook to run in CVS checkout before committing to CVS branch <branch>

    posthook.git.<branch> = <command> <args> # hook to run in Git clone after committing to Git branch <branch> or exporting it to CVS
    posthook.imp.git.<branch> = <command> <args> # hook to run in Git clone after committing to Git branch <branch> from CVS
    posthook.exp.git.<branch> = <command> <args> # hook to run in Git clone after committing to CVS from Git branch <branch>
    posthook.cvs.<branch> = <command> <args> # hook to run in CVS checkout after committing to CVS branch <branch>

The `gitroot`, `cvsroot`, `email`, `skeleton` keys, and general
(non-branch-specific) hooks, may be in the `GLOBAL` section. Entries
in the `GLOBAL` section will be overridden by any specific
per-repository values.  The `branchfrom` and all branch-specific
keys (`cvs.*`, `git.*`, `merge.*`, and `prefix.*`) must be specified
only in specific repository sections.

Each repository is specified by the path relative to the `gitroot`
and the *basename* must be unique for all repositories that share
working directories.  Bigitr will enforce that the basenames are
unique for a particular repository configuration file.  If you
cannot guarantee uniqueness between repository configuration files,
then you must use different work directories in different application
configuration (`global.logdir`, `global.gitdir`, `import.cvsdir`, and
`export.cvsdir`) for each repository configuration.

skeleton files are used only when creating a new `cvs-*` import branch.
Note that changing the skeleton between creating `cvs-*` import branches
will introduce merge conflicts when you merge `cvs-*` branches into
Git development branches.  Any skeleton files other than `.git*` files
will be included in the files exported from Git branches to CVS branches.
The normal use of a skeleton is to introduce a `.gitignore` file that is
different from `.cvsignore` and/or a `.gitattributes` file; if there is no
skeleton and there is a top-level `.cvsignore` file, new branches will
include the contents of `.cvsignore` as the initial `.gitignore` contents.

For each `git.<branch>`, `export-<branch>` in Git is used to track what
on `<branch>` has been exported to CVS.  This branch never has anything
committed to it.  It only gets fast-forward merges from `<branch>`.  It
is used to track what is new in order to create commit messages.

`merge.<sourcebranch> = <targetbranch>` specifies merges to attempt; if
git reports a successful merge with a 0 return code, the merge will
be pushed.  This merge will be done after operations that modify
`<sourcebranch>`, such as importing a cvs branch into git, or another
merge operation.  Typical usage is therefore:

    merge.cvs-foo = bar baz
    merge.bar = master

This would mean that when the `foo` branch is imported from cvs, it
will be merged onto the `bar` and `baz` branches in git; furthermore,
if the merge onto `bar` is successful, `bar` will then be merged onto
`master`.

When doing a git branch export with `export.preimport = true`,
if there are any merge failures from the preimport, then the git
branch export will be aborted.

All hooks are run in the obvious directory; git hooks are run in a
git working directory with the specified branch checked out, and
cvs hooks are run in a cvs checkout in which the specified branch
is a sticky tag.  The pre hooks are run before a commit operation,
and post hooks are run after all post-commit operations are complete;
for example, the cvs post hooks are run after fast-forwarding the
export- branch.  Git post hooks are run before merging downstream
branches, and Git post hooks (but not pre hooks at this time; this
may be changed later) are run for each merge target as well as for
cvs import branches.

Per-branch hooks (e.g. prehook.git.master) are run in addition to
general hooks (e.g. prehook.git) and the general hooks are run
first.  Per-direction hooks (e.g. prehook.imp.git,
prehook.imp.git.master) are are run after their bidirectional
equivalents.

Hooks that modify Git state are generally discouraged.  Committing
may invalidate invariants and cause unexpected operation.
Changing branches will almost certainly break in terrible and
unexpected ways.  The main use for pre hooks is to normalize the
contents of files to be committed in ways that are not implemented
as specific configuration.  The main use for post hooks is arbitrary
notification.


Requirements
============

Bigitr depends on precise behavior of Git and CVS, and on the "-i"
option to sed.  The behavior of this tool should be validated after
ANY update to any of the programs which it calls: git, cvs, and sed,
as well as after any other update that might affect them (libraries,
system language configuration, etc.).  A test suite is provided to
help validate this behavior.  If you discover failures not exposed by
the test suite, please augment the test suite.  In particular,
additional functional tests or story tests would be appropriate.
This tool automates only (part of) the **process** of synchronization
between Git and CVS branches.  It does not automate any **monitoring**
of the results.  *Do not relax monitoring because you are using it.*
For example, if you have changemail notification on CVS, do not disable
it for branches that are developed in Git and pushed to CVS; use that
changemail to confirm that the synchronization process has worked.

Bigitr also assumes essentially unlimited argument length, as it
passes arbitrarily many file names on the command line.  This limits
it to working on relatively recent Linux kernels (2.6.23 and later)
for large repositories.  At least Python 2.5 is required (due to the
use of "with").

Bigitr requires nose (may be packaged as python-nose), coverage
(may be packaged as python-coverage), and mock (may be packaged as
python-mock).  The documentation is maintained in markdown.
