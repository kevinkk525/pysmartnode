#!/usr/bin/env bash
pip3 install strip-hints
cd /mnt/r/pysmartnode
function foo {
                   echo $1
                   local res=$(/home/kevin/.local/bin/strip-hints --only-assigns-and-defs --only-test-for-changes $1)
                   if [[ $res = "True" ]]; then
                       echo "$1 stripped of hints"
                       v=$(/home/kevin/.local/bin/strip-hints --only-assigns-and-defs $1)
                       echo "$v" > $1
                   #else
                   #    echo $1 $res
                   fi
                }
export -f foo
find . -name \*.py -exec bash -c 'foo "$@"' bash {} \;