#!/usr/bin/env python3
import os

resources = {}

os.chdir('../src/')

def process_file(name):
    if name.endswith('.gitignore'):
        return
    if name.endswith('.py'):
        return
    print('processing file %s' % name)
    with open(name, 'rb') as f:
        resources[name] = f.read()

# scan common resources
for res in os.scandir('trezor/res/'):
    if res.is_file():
        process_file('trezor/res/%s' % res.name)

# scan apps
for app in os.scandir('apps/'):
    if app.is_dir() and os.path.isdir('apps/%s/res/' % app.name):
        for res in os.scandir('apps/%s/res/' % app.name):
            if res.is_file():
                process_file('apps/%s/res/%s' % (app.name, res.name))

resfile = 'trezor/res/resources.py'
with open(resfile, 'wt') as f:
    f.write('resdata = {\n')
    for k in sorted(resources.keys()):
        f.write("    '%s': %s,\n" % (k, resources[k]))
    f.write('}\n')

print('written %s with %d entries' % (resfile, len(resources)))
