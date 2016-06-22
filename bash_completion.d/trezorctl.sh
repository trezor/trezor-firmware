_trezorctl()
{
    local cur prev cmds base
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    cmds=$(trezorctl --help | grep -A 1 'Available commands:' | tail -n 1 | tr '{},' '   ')

    COMPREPLY=($(compgen -W "${cmds}" -- ${cur}))
    return 0
}

complete -F _trezorctl trezorctl
