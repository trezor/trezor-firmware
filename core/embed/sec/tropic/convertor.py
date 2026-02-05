import json
import yaml
from pprint import pprint

def get_raw_data(filename:str) -> str:
    with open(filename, "r") as file:
        return file.read()

def extract_json_data(raw_data:str):
    lines = raw_data.splitlines()
    lines = [line.strip() for line in lines]
    i_config_data = [line for line in lines if line.startswith("~0U")]
    r_config_data = [line for line in lines if line.startswith("0") or line.startswith("BIT")]

    return i_config_data, r_config_data


def parse_i_config_data(i_config_data, config_names) -> dict:
    new_data = {}
    i = 0
    for line in i_config_data:
        name = config_names[i]
        if line.endswith(","):
            line = line[:-1]
        if line.startswith("~0U"):
            line = line[3:]
        line = line.replace(" & ~BIT(", ", ").replace(")", "")
        numbers = [int(x) for x in line.split(", ") if x.isdigit()]
        new_data[name] = {"all_except": numbers}
        i += 1
    return new_data


def parse_r_config_data(r_config_data, config_names) -> dict:
    new_data = {}
    i = 0
    for line in r_config_data:
        numbers = []
        name = config_names[i]
        if line.endswith(","):
            line = line[:-1]
        if line.startswith("BIT"):
            line = line.replace(' | ', ', ')
            line = line.replace("BIT(", "").replace(")", "")
            numbers = [int(x) for x in line.split(", ") if x.isdigit()]
        new_data[name] = {"bits": numbers}
        i += 1
    return new_data

def get_config_names(raw_data):
    lines = raw_data.splitlines()
    lines = [line.strip() for line in lines]
    config_names_1 = []
    config_names_2 = []
    for line in lines:
        if line.startswith("// # CFG_"):
            name = line[4:].strip()
            name = name[:name.find("(0x")]
            name = name.lower().strip()
            if len(config_names_1) < 27:
                config_names_1.append(name)
            else:
                config_names_2.append(name)
    assert len(config_names_1) == 27
    assert len(config_names_2) == 27
    assert config_names_1 == config_names_2
    return config_names_1

def save(i_config, r_config, output_name):
    output_data = {
        "irreversible_configuration": i_config,
        "reversible_configuration": r_config
    }
    with open(output_name, "w") as outfile:
        json.dump(output_data, outfile, indent=2)


def make_save(file_name, output_name):
    raw_data = get_raw_data(file_name)
    i_config_data, r_config_data = extract_json_data(raw_data)
    config_names = get_config_names(raw_data)
    i_config = parse_i_config_data(i_config_data, config_names)
    r_config = parse_r_config_data(r_config_data, config_names)
    save(i_config, r_config, output_name)

def check_save(output_filename, check_filename):
    with open(output_filename, "r") as outfile:
        output_data = json.load(outfile)
    with open(check_filename, "r") as checkfile:
        check_data = json.load(checkfile)

    assert output_data.keys() == check_data.keys(), "Output and check data keys do not match!"
    assert output_data["irreversible_configuration"].keys() == check_data["irreversible_configuration"].keys(), "Irreversible configuration keys do not match!"
    assert output_data["reversible_configuration"].keys() == check_data["reversible_configuration"].keys(), "Reversible configuration keys do not match!"

    for key in output_data["irreversible_configuration"].keys():
        assert output_data["irreversible_configuration"][key] == check_data["irreversible_configuration"][key], f"Irreversible configuration for key {key} does not match!"
    for key in output_data["reversible_configuration"].keys():
        assert output_data["reversible_configuration"][key] == check_data["reversible_configuration"][key], f"Reversible configuration for key {key} does not match!"

    assert output_data == check_data, "Generated data does not match the manual data!"


def check_header_files():
    original = "core/embed/sec/tropic/inc/sec/tropic_configs.h"
    generated = "core/embed/sec/tropic/inc/sec/header_maker.h"

    with open(original, "r") as orig_file:
        orig_data = orig_file.read()
    with open(generated, "r") as gen_file:
        gen_data = gen_file.read()

    gen_warning = """// generated from header_maker.py.mako
// (by running `make templates` in `core`)
// do not edit manually!

"""
    assert gen_warning + orig_data == gen_data, "Header files do not match!"


def json_to_yaml(json_name, yaml_name):
    with open(json_name, "r") as json_file:
        json_data = json.load(json_file)

    with open(yaml_name, "w") as yaml_file:
        yaml.dump(json_data, yaml_file, sort_keys=False, default_flow_style=None)



def josn_c_to_yaml_with_comments(json_name, c_name, yaml_name):
    with open(json_name, "r") as json_file:
        json_data = json.load(json_file)

    with open(c_name, "r") as c_file:
        c_data = c_file.read()

    comments = {"irreversible_configuration": {}, "reversible_configuration": {}}
    lines = c_data.splitlines()
    current_key = None
    configuration = None
    name = None

    with open(yaml_name, "w") as yaml_file:
        for line in lines:
            line = line.strip()
            if line.startswith("const struct lt_config_t"):
                if "irreversible_configuration" in line:
                    configuration = "irreversible_configuration"
                    current_key = None
                    name = None
                    yaml_file.write("irreversible_configuration:\n")
                elif "reversible_configuration" in line:
                    configuration = "reversible_configuration"
                    current_key = None
                    name = None
                    yaml_file.write("reversible_configuration:\n")
            elif line.startswith("// # CFG_"):
                name = line[4:].strip()
                name = name[:name.find("(0x")]
                name = name.lower().strip()
                current_key = name
                comments[configuration][current_key] = []
                comment_line = line[2:].strip()
                comments[configuration][current_key].append(comment_line)
            elif current_key and line.startswith("//"):
                comment_line = line[2:].strip()
                comments[configuration][current_key].append(comment_line)
            else: # value line
                current_key = None
                if name is None:
                    continue
                yaml_file.write(f"  {name}:\n")
                for comment in comments[configuration][name]:
                    yaml_file.write(f"    # {comment}\n")
                yaml_file.write(f"    {json_data[configuration][name]}\n\n")

def yaml_check(yaml_name, json_name):
    with open(yaml_name, "r") as yaml_file:
        yaml_data = yaml.safe_load(yaml_file)

    with open(json_name, "r") as json_file:
        json_data = json.load(json_file)

    assert yaml_data == json_data, "YAML data does not match JSON data!"

if __name__ == "__main__":
    json_name = "core/embed/sec/tropic/tropic_configs.json"
    yaml_name = "core/embed/sec/tropic/tropic_configs.yaml"
    c_name = "core/embed/sec/tropic/tropic_configs.c"
    # json_to_yaml(json_name, yaml_name)
    josn_c_to_yaml_with_comments(json_name, c_name, yaml_name)
    yaml_check(yaml_name, json_name)


