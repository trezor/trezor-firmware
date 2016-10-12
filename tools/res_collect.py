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
    if os.path.basename(name).startswith('.'):
        return
    with open(name, 'rb') as f:
        data = f.read()
        resources[name] = data
        print('processing file %s (%d bytes)' % (name, len(data)))
        global resources_size
        resources_size += len(data)


def process_dir_rec(dir):
    for name in os.listdir(dir):
        path = os.path.join(dir, name)
        if os.path.isfile(path):
            process_file(path)
        elif os.path.isdir(path):
            process_dir_rec(path)


process_dir_rec('trezor/res/')
for name in os.listdir('apps/'):
    path = os.path.join('apps/', name, 'res/')
    if os.path.isdir(path):
        process_dir_rec(path)

resfile = 'trezor/res/resources.py'
with open(resfile, 'wt') as f:
    f.write('resdata = {\n')
    for k in sorted(resources.keys()):
        f.write("    '%s': %s,\n" % (k, resources[k]))
    f.write('}\n')

print('written %s with %d entries (total %d bytes)' %
      (resfile, len(resources), resources_size))
