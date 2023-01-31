set pagination off
set print array on
set print pretty on
# pwd is core/src
set logging file ../tools/gdb_scripts/layout_size.log
set logging on

break src/ui/layout/obj.rs:122
commands 1
  print "Size of current root layout"
  print sizeof(root)
  print root

  # not stopping the debugger
  continue
end

run
