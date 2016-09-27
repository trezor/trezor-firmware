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
for res in os.listdir('trezor/res/'):
    name = os.path.join('trezor/res/', res)
    if os.path.isfile(name):
        process_file(name)

# scan apps
for app in os.listdir('apps/'):
    name = os.path.join('apps/', app)
    if os.path.isdir(name) and os.path.isdir('apps/%s/res/' % app):
        for res in os.listdir('apps/%s/res/' % app):
            name = 'apps/%s/res/%s' % (app, res)
            if os.path.isfile(name):
                process_file(name)

resfile = 'trezor/res/resources.py'
with open(resfile, 'wt') as f:
    f.write('resdata = {\n')
    for k in sorted(resources.keys()):
        f.write("    '%s': %s,\n" % (k, resources[k]))
    f.write('}\n')

print('written %s with %d entries' % (resfile, len(resources)))
