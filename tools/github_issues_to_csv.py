"""
Taken from  https://gist.github.com/patrickfuller/e2ea8a94badc5b6967ef3ca0a9452a43 and modified.

Currently writes all issues that have some Weight.
"""
import argparse
import csv
from getpass import getpass
import requests

auth_id = None
auth_secret = None

PRIORITIES = ("P1", "P2", "P3", "P4")
SEVERITIES = ("S1", "S2", "S3", "S4")
WEIGHTS = ("W0", "W1/2", "W1", "W2", "W3", "W5", "W8", "W13", "W20", "W40", "W100")

def write_issues(r, csvout):
    """Parses JSON response and writes to CSV."""
    if r.status_code != 200:
        raise Exception(r.status_code)
    for issue in r.json():
        if 'pull_request' not in issue:
            priority = ""
            severity = ""
            weight = ""
            labels = []
            for l in issue['labels']:
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
            date = issue['created_at'].split('T')[0]
            milestone =  issue['milestone']['title'] if issue['milestone'] else ""

            csvout.writerow([issue['title'], issue['number'], issue['html_url'], issue['state'],
                milestone, priority, severity, weight, labels])


def get_issues(name):
    """Requests issues from GitHub API and writes to CSV file."""
    if auth_secret:
        url = 'https://api.github.com/repos/{}/issues?state=all&client_id={}&client_secret={}'.format(name, auth_id, auth_secret)
    else:
        url = 'https://api.github.com/repos/{}/issues?state=all'.format(name)
    r = requests.get(url)

    csvfilename = '{}-issues.csv'.format(name.replace('/', '-'))
    with open(csvfilename, 'w', newline='') as csvfile:
        csvout = csv.writer(csvfile)
        csvout.writerow(['Title', 'Number', 'URL', 'State', 'Milestone', 'Priority', 'Severity', 'Weight', 'Labels'])
        write_issues(r, csvout)

        # Multiple requests are required if response is paged
        if 'link' in r.headers:
            pages = {rel[6:-1]: url[url.index('<')+1:-1] for url, rel in
                     (link.split(';') for link in
                      r.headers['link'].split(','))}
            while 'last' in pages and 'next' in pages:
                pages = {rel[6:-1]: url[url.index('<')+1:-1] for url, rel in
                         (link.split(';') for link in
                          r.headers['link'].split(','))}
                r = requests.get(pages['next'])
                write_issues(r, csvout)
                if pages['next'] == pages['last']:
                    break


parser = argparse.ArgumentParser(description="Write GitHub repository issues "
                                             "to CSV file.")
parser.add_argument('repositories', nargs='+', help="Repository names, "
                    "formatted as 'username/repo'")
parser.add_argument('--all', action='store_true', help="Returns both open "
                    "and closed issues.")
args = parser.parse_args()

for repository in args.repositories:
    get_issues(repository)
