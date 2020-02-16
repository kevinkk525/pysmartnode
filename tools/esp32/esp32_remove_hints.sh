#!/usr/bin/env bash
#pip3 install strip-hints
cd ~/PycharmProjects/py-node/tools/esp32/dockercontainer-mpy-esp32-cc/mods # Todo: change Dirpath
function foo {
                   echo $1
                   local res=$(/home/tholo/.local/bin/strip-hints --only-assigns-and-defs --only-test-for-changes $1)
                   if [[ $res = "True" ]]; then
                       echo "$1 stripped of hints"
                       v=$(/home/tholo/.local/bin/strip-hints --only-assigns-and-defs $1)
                       echo "$v" > $1
                   #else
                   #    echo $1 $res
                   fi
                }
export -f foo
find . -name \*.py -exec bash -c 'foo "$@"' bash {} \;
cd ~/PycharmProjects/py-node/tools/esp32/dockercontainer-mpy-esp32-cc/1.12/def/mpscripts
find . -name \*.py -exec bash -c 'foo "$@"' bash {} \;
cd ~/PycharmProjects/py-node/tools/esp32/dockercontainer-mpy-esp32-cc/1.12/spiram/mpscripts
find . -name \*.py -exec bash -c 'foo "$@"' bash {} \;