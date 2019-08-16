"""
Exports issues from a list of repositories to individual csv files.
Uses basic authentication (Github username + password) to retrieve issues
from a repository that username has access to. Supports Github API v3.
Forked from: unbracketed/export_repo_issues_to_csv.py
"""
import argparse
import csv
from getpass import getpass
import requests

auth = None
state = 'open'


def write_issues(r, csvout):
    """Parses JSON response and writes to CSV."""
    if r.status_code != 200:
        raise Exception(r.status_code)
    for issue in r.json():
        if 'pull_request' not in issue:
            labels = ', '.join([l['name'] for l in issue['labels']])
            date = issue['created_at'].split('T')[0]
            # Change the following line to write out additional fields
            csvout.writerow([labels, issue['title'], issue['state'], date,
                             issue['html_url']])


def get_issues(name):
    """Requests issues from GitHub API and writes to CSV file."""
    url = 'https://api.github.com/repos/{}/issues?state={}'.format(name, state)
    r = requests.get(url, auth=auth)

    csvfilename = '{}-issues.csv'.format(name.replace('/', '-'))
    with open(csvfilename, 'w', newline='') as csvfile:
        csvout = csv.writer(csvfile)
        csvout.writerow(['Labels', 'Title', 'State', 'Date', 'URL'])
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
                r = requests.get(pages['next'], auth=auth)
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

if args.all:
    state = 'all'

username = input("Username for 'https://github.com': ")
password = getpass("Password for 'https://{}@github.com': ".format(username))
auth = (username, password)
for repository in args.repositories:
    get_issues(repository)