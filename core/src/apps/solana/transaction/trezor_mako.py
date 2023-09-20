from json import load

from mako.template import Template

with open("./core/src/apps/solana/transaction/programs.json", "r") as file:
    programs = load(file)

init_template = Template(
    filename="./core/src/apps/solana/transaction/instructions.py.mako"
)
with open("./core/src/apps/solana/transaction/instructions.py", "wt") as output:
    output.write(init_template.render(programs=programs))

pass
