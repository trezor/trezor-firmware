import re
import sys

QSTR_BLACKLIST = set(['NULL', 'number_of'])


def process(source, target):
    re_qstr = re.compile(r'MP_QSTR_[_a-zA-Z0-9]+')
    for line in source:
        for match in re_qstr.findall(line):
            name = match.replace('MP_QSTR_', '')
            if name not in QSTR_BLACKLIST:
                target.write('Q(%s)\n' % name)


if __name__ == '__main__':
    process(sys.stdin, sys.stdout)
