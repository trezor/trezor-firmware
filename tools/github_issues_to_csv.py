"""
Taken from  https://gist.github.com/patrickfuller/e2ea8a94badc5b6967ef3ca0a9452a43 and modified.

Currently writes all issues that have some Weight.
"""
import argparse
import csv
import requests
import os.path

token = None

path = os.path.dirname(os.path.realpath(__file__))
filename = path + "/github_issues_to_csv.ignore"
if os.path.exists(filename):
    with open(filename, "r") as config:
        content = config.read()
        if len(content) == 40:
            token = content
        else:
            raise ValueError("Invalid config file")

PRIORITIES = ("P1", "P2", "P3", "P4")
SEVERITIES = ("S1", "S2", "S3", "S4")
WEIGHTS = ("W0", "W1/2", "W1", "W2", "W3", "W5", "W8", "W13", "W20", "W40", "W100")


def write_issues(r, csvout):
    """Parses JSON response and writes to CSV."""
    if r.status_code != 200:
        raise Exception(r.status_code)
    for issue in r.json():
        if "pull_request" not in issue:
            priority = ""
            severity = ""
            weight = ""
            labels = []
            for l in issue["labels"]:
                if l["name"][:2] in PRIORITIES:
                    priority = l["name"]
                elif l["name"][:2] in SEVERITIES:
                    severity = l["name"]
                elif l["name"] in WEIGHTS:
                    weight = l["name"][1:]
                    if weight == "1/2":
                        weight = "0.5"
                else:
                    labels.append(l["name"])
            if not weight:
                continue
            labels = ", ".join(labels)
            date = issue["created_at"].split("T")[0]
            milestone = issue["milestone"]["title"] if issue["milestone"] else ""
            assignee = issue["assignee"]["login"] if issue["assignee"] else ""

            csvout.writerow(
                [
                    issue["title"],
                    issue["number"],
                    issue["html_url"],
                    issue["state"],
                    assignee,
                    milestone,
                    priority,
                    severity,
                    weight,
                    labels,
                ]
            )


def get_issues(name):
    """Requests issues from GitHub API and writes to CSV file."""
    url = "https://api.github.com/repos/{}/issues?state=all".format(name)
    if token is not None:
        headers = {"Authorization": "token " + token}
    else:
        headers = None
    r = requests.get(url, headers=headers)

    csvfilename = "{}-issues.csv".format(name.replace("/", "-"))
    with open(csvfilename, "w", newline="") as csvfile:
        csvout = csv.writer(csvfile)
        csvout.writerow(
            [
                "Title",
                "Number",
                "URL",
                "State",
                "Assignee",
                "Milestone",
                "Priority",
                "Severity",
                "Weight",
                "Labels",
            ]
        )
        write_issues(r, csvout)

        # Multiple requests are required if response is paged
        if "link" in r.headers:
            pages = {
                rel[6:-1]: url[url.index("<") + 1 : -1]
                for url, rel in (
                    link.split(";") for link in r.headers["link"].split(",")
                )
            }
            while "last" in pages and "next" in pages:
                pages = {
                    rel[6:-1]: url[url.index("<") + 1 : -1]
                    for url, rel in (
                        link.split(";") for link in r.headers["link"].split(",")
                    )
                }
                r = requests.get(pages["next"], headers=headers)
                write_issues(r, csvout)
                if pages["next"] == pages["last"]:
                    break


parser = argparse.ArgumentParser(
    description="Write GitHub repository issues " "to CSV file."
)
parser.add_argument(
    "repositories", nargs="+", help="Repository names, " "formatted as 'username/repo'"
)
parser.add_argument(
    "--all", action="store_true", help="Returns both open " "and closed issues."
)
args = parser.parse_args()

for repository in args.repositories:
    get_issues(repository)
