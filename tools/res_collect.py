#!/usr/bin/env python3
import os

resources = {}
resources_size = 0

os.chdir(os.path.dirname(__file__))
os.chdir('../src/')

def process_file(name):
    if name.endswith('.gitignore'):
        return
    if name.endswith('.py'):
        return
    with open(name, 'rb') as f:
        data = f.read()
        resources[name] = data
        print('processing file %s (%d bytes)' % (name, len(data)))
        global resources_size
        resources_size += len(data)

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

print('written %s with %d entries (total %d bytes)' % (resfile, len(resources), resources_size))
