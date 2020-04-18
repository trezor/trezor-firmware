#!/usr/bin/env python3
import glob
import os
import subprocess

TREZOR_REPO = "https://github.com/trezor"

NAME="monorepo"
MAIN_REPO = "trezor-core"
SUBREPOS = {
    "trezor-common": "common",
    "trezor-crypto": "crypto",
    "trezor-mcu": "legacy",
    "trezor-storage": "storage",
    "python-trezor": "python",
}
PUBLISHED_SUBREPOS = ["trezor-common", "trezor-crypto"]

KEEP_TAGS = ["trezor-core", "trezor-mcu", "python-trezor"]

GITSUBREPO_TEMPLATE = """\
; DO NOT EDIT (unless you know what you are doing)
;
; This subdirectory is a git "subrepo", and this file is maintained by the
; git-subrepo command. See https://github.com/git-commands/git-subrepo#readme
;
[subrepo]
	remote = git+ssh://git@github.com/trezor/{remote}
	branch = master
	commit = {remote_head}
	parent = {current_head}
	method = rebase
	cmdver = 0.4.0
"""


def lines(s):
    yield from s.strip().split("\n")


def git(args):
    print("+ git:", args)
    return subprocess.check_output("git " + args, universal_newlines=True, shell=True)


def move_to_subtree(remote, dst):
    os.makedirs(dst, exist_ok=True)
    for fn in lines(git(f"ls-tree --name-only remotes/{remote}/master")):
        if fn == ".gitmodules":
            continue
        git(f"mv {fn} {dst}/{fn}")


def rewrite_gitmodules(remote, dst):
    master_gitmodules = git("show master:.gitmodules")
    try:
        gitmodules = git(f"show {remote}/master:.gitmodules")
    except:
        # no gitmodules
        return
    gitmodules = gitmodules.replace('submodule "', f'submodule "{dst}/')
    with open(".gitmodules", "w") as f:
        f.write(master_gitmodules + gitmodules)
    git("add .gitmodules")


def merge_remote(remote, dst):
    git(f"remote add {remote} {TREZOR_REPO}/{remote}")
    git(f"fetch {remote}")
    try:
        git(f"merge --no-commit --allow-unrelated-histories {remote}/master")
    except:
        # this might fail because of .gitmodules conflict
        pass

    rewrite_gitmodules(remote, dst)
    move_to_subtree(remote, dst)


def retag_remote(remote, dst):
    for tagline in lines(git(f"ls-remote -t {remote}")):
        commit, tagpath = tagline.split()
        tagname = os.path.basename(tagpath)
        git(f"tag {dst}/{tagname} {commit}")
        git(f"tag -d {tagname}")


def generate_subrepo_file(remote):
    current_head = git("rev-parse master").strip()
    remote_head = git(f"rev-parse {remote}/master").strip()
    dst = SUBREPOS[remote]
    with open(f"{dst}/.gitrepo", "w") as f:
        f.write(GITSUBREPO_TEMPLATE.format(remote=remote, current_head=current_head, remote_head=remote_head))
    git(f"add {dst}/.gitrepo")


def main():
    git(f"clone {TREZOR_REPO}/{MAIN_REPO} {NAME}")
    os.chdir(NAME)
    move_to_subtree("origin", "core")
    git(f"commit -m 'MONOREPO CREATE FROM {MAIN_REPO}'")
    retag_remote("origin", "core")

    for remote, dst in SUBREPOS.items():
        merge_remote(remote, dst)

        if remote in PUBLISHED_SUBREPOS:
            with open(f"{dst}/.gitmodules", "w") as f:
                f.write(git(f"show {remote}/master:.gitmodules"))
            git(f"add {dst}/.gitmodules")

        git(f"commit -m 'MONOREPO MERGE {remote}'")

        try:
            retag_remote(remote, dst)
        except:
            pass

    for submodule in glob.glob("*/vendor/*"):
        modname = os.path.basename(submodule)
        if modname not in SUBREPOS:
            continue

        git(f"rm {submodule}")
        symlink_target = f"../../{SUBREPOS[modname]}"
        os.symlink(symlink_target, submodule)
        git(f"add {submodule}")

    git(f"commit -m 'MONOREPO RELINK SUBMODULES'")

    for remote in PUBLISHED_SUBREPOS:
        generate_subrepo_file(remote)
    git(f"commit -m 'MONOREPO SUBREPO FILES'")


if __name__ == "__main__":
    main()
