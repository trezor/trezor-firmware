_trezorctl()
{
    export TREZORCTL_COMPLETION_CACHE
    local cur prev cmds base

    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    if [ -z "$TREZORCTL_COMPLETION_CACHE" ]; then
        help_output=$(trezorctl --help | grep '^  [a-z]' | awk '{ print $1 }')
        export TREZORCTL_COMPLETION_CACHE="$help_output"
    fi

    cmds="$TREZORCTL_COMPLETION_CACHE"

    COMPREPLY=($(compgen -W "${cmds}" -- ${cur}))
    return 0
}

complete -F _trezorctl trezorctl
