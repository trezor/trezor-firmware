ROOT=$1
NEW_ROOT="core/src/apps/ethereum/clear_signing_definitions"

imports=""
print $ROOT
find "$ROOT" -type f -name '*.json' | while read -r file; do
  rel_path=$(realpath --relative-to="$ROOT" "$file")
  new_path="$NEW_ROOT/${rel_path%.json}.py"
  new_path="${new_path//-/_}"
  #new_path="${new_path//\./_}"
  dir_part=$(dirname "$new_path")
	output=$(uv run core/tools/ethereum/parse_erc7730_json.py "$file")
	status=$?
	if [ $status -eq 0 ]; then
	    mkdir -p "$dir_part"
		touch "$dir_part/__init__.py"
		mod="${new_path//\//.}"
		mod="${mod#core.src.}"
		mod="${mod%.py}"
		imports+="from $mod import DISPLAY_FORMATS"$'\n'
		imports+="for d in DISPLAY_FORMATS:"$'\n'
		imports+="    ALL_DISPLAY_FORMATS.append(d)"$'\n'
        echo "$output" > $new_path
    fi
	printf "%s" "$imports"
done

