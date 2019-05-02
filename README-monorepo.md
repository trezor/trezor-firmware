Monorepo notes
==============


Generating
----------

Use the [create_monorepo] script to regenerate from current master(s).

[create_monorepo]: create_monorepo.py


Structure
---------

This is a result of Git merge of several unrelated histories, each of which is
moved to its own subdirectory during the merge.

That means that this is actually all the original repos at the same time. You can
check out any historical commit hash, or any historical tag.

All tags from the previous history still exist, and in addition, each has a version
named by its directory. I.e., for trezor-mcu tag `v1.6.3`, you can also check out
`legacy/v1.6.3`.


Merging pre-existing branches
-----------------------------

Because the repository shares all the histories, merging a branch or PR can be done
with a simple `git merge`. It's often necessary to add hints to git by specifying a merge strategy - especially when some commits add new files.

Use the following options: `-s subtree -X subtree=<destdir>`.

Example for your local checkout:

    $ git remote add core-local ~/git/trezor-core
    $ git fetch core-local
    $ git merge core-local/wip -s subtree -X subtree=core

Same options should be used for `git rebase` of a pre-existing branch.


Sub-repositories
----------------

The monorepo has two subdirectories that can be exported to separate repos:

* **common** exports to https://github.com/trezor/trezor-common
* **crypto** exports to https://github.com/trezor/trezor-crypto

These exports are managed with [git-subrepo] tool. To export all commits that touch
one of these directories, run the following command:

    $ git subrepo push <dirname>

You will need commit access to the respective GitHub repository.

For installation instructions and detailed usage info, refer to the [git-subrepo] README.

[git-subrepo]: https://github.com/ingydotnet/git-subrepo

---

Sketch of further details:

What git-subrepo does under the hood is create and fetch a remote for the export,
check out `parent` revision and replay all commits since `commit` using
something along the lines of `git filter-branch --subdirectory-filter`.

So basically a nicely tuned git-subtree.

This can all be done manually if need be (or if you need more advanced usecases like
importing changes from the repo commit-by-commit, because git-subrepo will squash
on import). See [this nice article](https://medium.com/@porteneuve/mastering-git-subtrees-943d29a798ec)
for hints.
