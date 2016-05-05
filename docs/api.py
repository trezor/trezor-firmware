#!/usr/bin/python3
import os

def process_file(fn):
    mod, ext = os.path.splitext(fn)
    src = open('../%s' % (fn)).readlines()
    r = []
    if ext in ['.h', '.c']:
        for l in src:
            l = l.rstrip()
            if l.startswith('/// '):
                r.append('``` python')
                r.append(l[4:])
                r.append('```')
    elif ext == '.py':
        mod = mod[4:].replace('/', '.')
        for l in src:
            l = l.rstrip()
            if l.startswith('def '):
                r.append('``` python')
                r.append('def %s.' % mod + l[4:-1])
                r.append('```')
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
