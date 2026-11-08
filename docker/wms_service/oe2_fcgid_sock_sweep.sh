#!/bin/sh
# Remove mod_fcgid socket files nothing has bound any more (bound unix sockets are listed in /proc/net/unix).
# mod_fcgid unlinks a socket when it reaps the process; sockets of processes it never reaped (killed process manager,
# crashed httpd generation) stay behind and eventually exhaust inodes/space under /etc/httpd/run/fcgidsock.
d=/etc/httpd/run/fcgidsock
[ -d "$d" ] || exit 0
n=0
for s in $(find "$d" -type s -mmin +10 2>/dev/null); do
  grep -qF " $s" /proc/net/unix && continue
  rm -f "$s" && n=$((n+1))
done
[ "$n" -gt 0 ] && echo "[$(date)] Removed $n stale mod_fcgid sockets" >> /var/log/onearth/config.log
exit 0
