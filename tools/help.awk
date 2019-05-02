#!/usr/bin/env awk
BEGIN {
    FS = ":.*?## "
    first = 1
    COLOR_BROWN = "\033[33m"
    COLOR_DARKGREEN = "\033[36m"
    COLOR_RESET = "\033[0m"
} /^[a-zA-Z0-9_-]+:.*?## / {
    printf COLOR_DARKGREEN
    printf "  make %-22s", $1
    printf COLOR_RESET
    printf " %s\n", $2
} /^##(.*)/ {
    if (!first)
        printf "\n"
    printf "%s%s\n", COLOR_BROWN, substr($0, 4)
    first = 0
}
