from mako.template import Template
from json import load
# from os import mkdir

with open("./core/src/apps/solana/instructions/programs.json", "r") as file:
    programs = load(file)

# try:
#     mkdir("./generated")
# except:
#     pass

# init_template = Template(filename="./mako_templates/__init__.py.mako")
# with open("./generated/__init__.py", "wt") as output:
#     output.write(init_template.render(programs = programs))

# for program in programs["programs"]:
#     # import file name
#     file_name = "_".join(program["name"].lower().split(" "))
#     with open("./generated/{0}.py".format(file_name), "wt") as output:
#         program_template = Template(filename="./mako_templates/program.py.mako")
#         output.write(program_template.render(program = program))


init_template = Template(filename="./core/src/apps/solana/instructions/instructions.py.mako")
with open("./core/src/apps/solana/instructions/instructions2.py", "wt") as output:
    output.write(init_template.render(programs = programs))



pass
