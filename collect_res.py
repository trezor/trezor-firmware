#!/usr/bin/env python3
import os

resources = {}

def process_file(name):
    if name.endswith('.py'):
        return
    with open(name, 'rb') as f:
        resources[name] = f.read()

# scan common resources
for res in os.scandir('src/trezor/res/'):
    if res.is_file():
        process_file('src/trezor/res/%s' % res.name)

# scan apps
for app in os.scandir('src/apps/'):
    if app.is_dir():
        for res in os.scandir('src/apps/%s/res/' % app.name):
            if res.is_file():
                process_file('src/apps/%s/res/%s' % (app.name, res.name))

with open('src/trezor/res/resources.py', 'wt') as f:
    f.write('resdata = ' + str(resources))
