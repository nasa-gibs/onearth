#!/bin/sh
# Remove per-container log directories under LOG_ROOT with no writes in the last DAYS days
LOG_ROOT="${ONEARTH_LOG_ROOT:-}"
DAYS="${ONEARTH_LOG_RETENTION_DAYS:-}"
SELF="$(cat /proc/sys/kernel/hostname)"
case "$DAYS" in
  ''|*[!0-9]*|0) DAYS=7 ;;
esac
[ -n "$LOG_ROOT" ] && [ -d "$LOG_ROOT" ] || exit 0
for dir in "$LOG_ROOT"/*/; do
  [ -d "$dir" ] || continue
  [ -f "$dir/.onearth-wms-logs" ] && [ ! -L "$dir/.onearth-wms-logs" ] || continue
  name=$(basename "$dir")
  [ "$name" = "$SELF" ] && continue
  if [ -z "$(find "$dir" -mtime "-$DAYS" -print -quit 2>/dev/null)" ]; then
    rm -rf "$dir" && echo "[$(date)] Removed stale log directory $dir"
  fi
done
exit 0
