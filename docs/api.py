#!/usr/bin/python3
import os
import re

def process_file(fn):
    mod, ext = os.path.splitext(fn)
    src = open('../%s' % (fn)).readlines()
    r = []
    cls = ''
    if ext in ['.h', '.c']:
        for l in src:
            l = l.rstrip()
            if l.startswith('/// def '):
                r.append('``` python')
                r.append(l[4:])
                r.append('```')
            elif l.startswith('/// '):
                r.append(l[4:])
            elif l == '///':
                r.append('')
    elif ext == '.py':
        mod = mod[4:].replace('/', '.')
        if mod.endswith('.__init__'):
            mod = mod[:-9]
        for l in src:
            l = l.rstrip()
            if l.startswith('def '):
                r.append('``` python')
                r.append('def %s.' % mod + l[4:-1])
                r.append('```')
            elif l.startswith('### '):
                r.append(l[4:])
            elif l.startswith('###'):
                r.append('')
            elif l.startswith('class '):
                cls = re.match('class ([A-Za-z0-9_]*)', l).group(1)
            elif l.startswith('    def ') and not l.startswith('    def __init__'):
                r.append('``` python')
                r.append('def %s.' %  cls + l[8:-1])
                r.append('```')
            elif l.startswith('    ### '):
                r.append(l[8:])
            elif l.startswith('    ###'):
                r.append('')
    return r

def main():
    tpl = open('api.template.md', 'rt').readlines()
    f = open('api.md', 'wt')
    for line in tpl:
        if line.startswith('@'):
            for l in process_file(line[1:].strip()):
                f.write(l + '\n')
        else:
            f.write(line)
    f.close()

if __name__ == "__main__":
    main()
