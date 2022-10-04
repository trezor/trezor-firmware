# Size (binsize)

Shell and python scripts acting as wrappers around `binsize` tool/command.

Adding `--help` to any `<command>.sh` will show the help message for that specific command.

Settings of this specific (`trezor-firmware`) project are forwarded in each command. Specifically, `core/build/firmware/firmware.elf` and `core/build/firmware/firmware.map` (optional) files are used and we are interested in `.flash` and `.flash2` sections.

`bloaty` and `nm` tools are needed.

For more info about `binsize` tool, visit [its repository](github.com/trezor/binsize).

## Available scripts/commands

### app.py
Shows the statistics about each micropython app.

### build.sh <file_suffix>
Builds the firmware with optional renaming of the generated .elf file.

### checker.py
Checks the size of the current firmware against the size limits of its flash sections.

### commit.sh <commit_id>
Gets the size difference introduced by a specified commit

### compare_master.py
Compares the size of the current firmware with the size of the latest master.

### compare.sh <old_elf_file> <new_elf_file>
Compares the size of two firmware binaries.

### get.sh
Gets the size information about the current firmware.

### groups.py
Shows the groupings of all symbols into specific categories.

### history.sh <commit_amount:int> <step_size:int>
Shows the size history of latest `<commit_amount>` with `<step_size>` commits  between them.
BEWARE: might not always work properly, as it needs to build firmware for each commit. It may happens that some commits are not buildable.

### tree.sh
Shows the tree-size view of all files in the current firmware with their sizes.
