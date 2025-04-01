import sys
block, = sys.argv[1:]
rows = list(l.strip().split('\t') for l in sys.stdin)

while int(block) > 0:
	row = next(r for r in rows if r[1] == block)
	print(''.join(f'{c:<8} ' for c in row))
	block = row[0]
