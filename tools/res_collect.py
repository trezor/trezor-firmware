#!/usr/bin/env python3
import os

resources = {}

os.chdir('..')

def process_file(name):
    if name.endswith('.gitignore'):
        return
    if name.endswith('.py'):
        return
    print('processing file %s' % name)
    with open(name, 'rb') as f:
        k = name[4:] # remove 'src/' at the beginning
        resources[k] = f.read()

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

resfile = 'src/trezor/res/resources.py'
with open(resfile, 'wt') as f:
    f.write('resdata = {\n')
    for k in sorted(resources.keys()):
        f.write("    '%s': %s,\n" % (k, resources[k]))
    f.write('}\n')

print('written %s with %d entries' % (resfile, len(resources)))
