# Open the DCU console once on interactive team logins; 'q' drops to the shell.
if [ -t 0 ] && [ -z "$DCU_CONSOLE_SHOWN" ] && id -nG | grep -qw teams; then
    export DCU_CONSOLE_SHOWN=1
    dcu
fi
