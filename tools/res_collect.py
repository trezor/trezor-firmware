#!/usr/bin/env python3
import os

resources = {}

os.chdir('..')

def process_file(name):
    if name.endswith('.gitignore'):
        return
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
    if app.is_dir() and os.path.isdir('src/apps/%s/res/' % app.name):
        for res in os.scandir('src/apps/%s/res/' % app.name):
            if res.is_file():
                process_file('src/apps/%s/res/%s' % (app.name, res.name))

with open('src/trezor/res/resources.py', 'wt') as f:
    f.write('resdata = {\n')
    for k in sorted(resources.keys()):
        f.write("    '%s': %s,\n" % (k, resources[k]))
    f.write('}\n')
