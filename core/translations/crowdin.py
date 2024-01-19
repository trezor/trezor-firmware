import subprocess
import tempfile
from pathlib import Path
import json
import sys
import os

HERE = Path(__file__).parent


def download() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        command = f"crowdin download --all --verbose --token $CROWDIN_TOKEN --base-path={temp_dir}"
        print("command", command)

        subprocess.run(command, shell=True, check=True)

        for directory in Path(temp_dir).iterdir():
            print("directory", directory)
            lang_name = directory.name
            en_file = directory / "en.json"
            if not en_file.exists():
                print("Skipping - no en.json inside", lang_name)
                continue
            print("Processing", lang_name)
            data = json.loads(en_file.read_text())
            lang_file = HERE / f"{lang_name}.json"
            if not lang_file.exists():
                print("Skipping - no lang_file on our side", lang_name)
                continue
            lang_file_data = json.loads(lang_file.read_text())
            lang_file_data["translations"] = data["translations"]
            lang_file.write_text(json.dumps(lang_file_data, indent=2, sort_keys=True, ensure_ascii=False)  + "\n")
            print("Translations updated", lang_name)


def upload() -> None:
    command = "crowdin upload sources --token $CROWDIN_TOKEN"
    print("command", command)

    subprocess.run(command, shell=True, check=True)


if __name__ == "__main__":
    if not os.environ.get("CROWDIN_TOKEN"):
        print("CROWDIN_TOKEN env variable not set")
        sys.exit(1)

    if "download" in sys.argv:
        download()
    elif "upload" in sys.argv:
        upload()
    else:
        print("Usage: python crowdin.py [download|upload]")
        sys.exit(1)
