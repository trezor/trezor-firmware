#!/usr/bin/env python3
"""
Automatic generator of documentation about CI jobs.
Analyzes all .yml files connected with CI, takes the most important information
and writes it into a README file.

Features:
- reads a job description from a comment above job definition
- includes a link to each file and also to job definition

Usage:
- put comments (starting with "#") directly above the job definition in .yml file

Running the script:
- `python generate_ci_docs.py` to generate the documentation
- `python generate_ci_docs.py --check` to check if documentation is up-to-date
"""

from __future__ import annotations

import argparse
import filecmp
import os
import re
import sys
from collections import OrderedDict
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import yaml
from mako.template import Template

parser = argparse.ArgumentParser()
parser.add_argument(
    "--check",
    action="store_true",
    help="Check if there are no new changes in all CI .yml files",
)
args = parser.parse_args()


class DocsGenerator:
    def __init__(self) -> None:
        # Going to the root directory, so the relative
        # locations of CI files are valid
        os.chdir(Path(__file__).resolve().parent.parent)

        self.GITLAB_CI_FILE = ".gitlab-ci.yml"
        self.DOC_FILE = "docs/ci/jobs.md"

        # Some keywords that are not job definitions and we should not care about them
        self.NOT_JOBS = [
            "variables:",
            "image:",
            ".gitlab_caching:",
        ]

        self.ALL_JOBS: dict[Path, dict[str, Any]] = OrderedDict()

        self.FILES = self.get_all_ci_files()

    def generate_docs(self) -> None:
        """Whole pipeline of getting and saving the CI information."""
        for file in self.FILES:
            self.ALL_JOBS[file] = {
                "jobs": self.get_jobs_from_file(file),
                "overall_description": self.get_overall_description_from_file(file),
            }

        self.save_docs_into_file()

    def verify_docs(self) -> None:
        """Checking if the docs are up-to-date with current CI .yml files.

        Creating a new doc file and comparing it against already existing one.
        Exit with non-zero exit code when these files do not match.
        """
        already_filled_doc_file = self.DOC_FILE

        with NamedTemporaryFile() as temp_file:
            self.DOC_FILE = temp_file.name

            self.generate_docs()
            if filecmp.cmp(already_filled_doc_file, self.DOC_FILE):
                print("SUCCESS: Documentation is up-to-date!")
                sys.exit(0)
            else:
                print("FAIL: Documentation is not up-to-date with CI .yml files!")
                print("    Please run this script or `make gen`")
                sys.exit(1)

    def get_all_ci_files(self) -> list[Path]:
        """Loading all the CI files which are used in Gitlab."""
        if not os.path.exists(self.GITLAB_CI_FILE):
            raise RuntimeError(
                f"Main Gitlab CI file under {self.GITLAB_CI_FILE} does not exist!"
            )

        with open(self.GITLAB_CI_FILE, "r") as f:
            gitlab_file_content = yaml.safe_load(f)

        all_ci_files = [Path(file) for file in gitlab_file_content["include"]]

        for file in all_ci_files:
            if not file.exists():
                raise RuntimeError(f"File {file} does not exist!")

        return all_ci_files

    @staticmethod
    def get_overall_description_from_file(file: Path) -> list[str]:
        """Looking for comments at the very beginning of the file."""
        description_lines: list[str] = []
        with open(file, "r") as f:
            for line in f:
                if line.startswith("#"):
                    # Taking just the text - no hashes, no whitespace
                    description_lines.append(line.strip("# \n"))
                else:
                    break

        return description_lines

    def get_jobs_from_file(self, file: Path) -> dict[str, dict[str, Any]]:
        """Extract all jobs and their details from a certain file."""
        all_jobs: dict[str, dict[str, Any]] = OrderedDict()

        # Taking all the comments above a non-indented non-comment, which is
        # always a job definition, unless defined in NOT_JOBS
        with open(file, "r") as f:
            comment_buffer: list[str] = []
            for index, line in enumerate(f):
                if line.startswith("#"):
                    # Taking just the text - no hashes, no whitespace
                    comment_buffer.append(line.strip("# \n"))
                else:
                    # regex: first character of a line is a word-character or a dot
                    if re.search(r"\A[\w\.]", line) and not any(
                        [line.startswith(not_job) for not_job in self.NOT_JOBS]
                    ):
                        job_name = line.rstrip(":\n")
                        all_jobs[job_name] = {
                            "description": comment_buffer,
                            "line_no": index + 1,
                        }
                    comment_buffer = []

        return all_jobs

    def save_docs_into_file(self) -> None:
        """Dump all the information into a documentation file."""

        template_text = """
# CI pipeline
(Generated automatically by `tools/generate_ci_docs.py`. Do not edit by hand.)

It consists of multiple stages below, each having one or more jobs
Latest CI pipeline of master branch can be seen at [${latest_master}](${latest_master})
<%
    ## Needed because "##" is a comment in Mako templates
    header_2 = "##"
    header_3 = "###"
%>
% for file, file_info in all_jobs_items:
${header_2} ${file.stem.upper()} stage - [${file.name}](https://github.com/trezor/trezor-firmware/blob/master/${file})
    % if file_info["overall_description"]:
        % for stage_overall_description_line in file_info["overall_description"]:
${stage_overall_description_line}
        % endfor
    % endif
    <%
        job_amount = f"{len(file_info['jobs'])} job{'s' if len(file_info['jobs']) > 1 else ''}"
    %>
Consists of **${job_amount}** below:
    % for job_name, job_info in file_info["jobs"].items():
        <%
            github_job_link = f"https://github.com/trezor/trezor-firmware/blob/master/{file}#L{job_info['line_no']}"
        %>
${header_3} [${job_name}](${github_job_link})
        % if job_info["description"]:
            % for job_description_line in job_info["description"]:
${job_description_line}
            %endfor
        % endif
    % endfor

---
% endfor
""".strip()

        with open(self.DOC_FILE, "w") as doc_file:
            doc_text: str = Template(template_text).render(
                latest_master="https://gitlab.com/satoshilabs/trezor/trezor-firmware/-/pipelines/master/latest",
                all_jobs_items=self.ALL_JOBS.items(),
            )
            # Remove trailing whitespace coming from the template and include final newline
            doc_file.writelines(line.rstrip() + "\n" for line in doc_text.splitlines())


if __name__ == "__main__":
    if args.check:
        DocsGenerator().verify_docs()
    else:
        DocsGenerator().generate_docs()
