set "variable=%1"
set "variable=%variable:\=/%"
set "p=/home/kevin/ws_cloud/Programme Python"
set "variable=%p%%variable%"
bash -c '"%variable%"  %2'