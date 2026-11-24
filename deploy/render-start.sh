#!/usr/bin/env bash
# One Render service + one persistent disk: Django API and the durable worker.
set -Eeuo pipefail
: "${SECRET_KEY:?Set SECRET_KEY in Render}"
export DATA_DIR="${DATA_DIR:-/var/data}"
export DATABASE_PATH="${DATABASE_PATH:-$DATA_DIR/db.sqlite3}"
export MEDIA_ROOT="${MEDIA_ROOT:-$DATA_DIR/media}"
mkdir -p "$(dirname "$DATABASE_PATH")" "$MEDIA_ROOT"

# The disk is available at runtime, not during build or pre-deploy.
python manage.py migrate --noinput

web_pid=""
worker_pid=""
cleanup() {
  trap - EXIT
  if [[ -n "$web_pid" ]]; then kill -TERM "$web_pid" 2>/dev/null || true; fi
  if [[ -n "$worker_pid" ]]; then kill -TERM "$worker_pid" 2>/dev/null || true; fi
  wait || true
}
trap cleanup EXIT
trap 'exit 143' TERM
trap 'exit 130' INT

if [[ -n "${GIMMECLIP_API_KEY:-}" && -n "${VIDEO_API_TOKEN:-}" ]]; then
  python -u manage.py run_video_worker &
  worker_pid=$!
else
  echo "Video worker disabled: configure GIMMECLIP_API_KEY and VIDEO_API_TOKEN to enable it."
fi
gunicorn tryon.wsgi:application --bind "0.0.0.0:${PORT:-10000}" \
  --workers 1 --threads 2 --timeout 240 --graceful-timeout 30 \
  --access-logfile - --error-logfile - &
web_pid=$!

# Do not leave an apparently healthy API running if its video worker dies.
set +e
children=("$web_pid")
if [[ -n "$worker_pid" ]]; then children+=("$worker_pid"); fi
wait -n "${children[@]}"
status=$?
set -e
if [[ "$status" -eq 0 ]]; then status=1; fi
exit "$status"
