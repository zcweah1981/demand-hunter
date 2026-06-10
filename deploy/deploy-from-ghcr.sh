#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/damand-hunter}"
REPO="${REPO:-zcweah1981/demand-hunter}"
BRANCH="${1:-main}"
TAG="${2:-main}"

mkdir -p "$APP_DIR/shared/data" "$APP_DIR/shared/output" "$APP_DIR/backups"
cd "$APP_DIR"

SHA="$(git ls-remote "https://github.com/$REPO.git" "refs/heads/$BRANCH" | awk '{print $1}')"
if [[ -z "$SHA" ]]; then
  echo "Cannot resolve $REPO@$BRANCH" >&2
  exit 1
fi
SHORT_SHA="${SHA:0:7}"

cat > "$APP_DIR/.deploy-version" <<EOF
repo=$REPO
branch=$BRANCH
sha=$SHA
tag=$TAG
deployed_at=$(date -Is)
EOF

export BACKEND_IMAGE="ghcr.io/zcweah1981/demand-hunter-backend:$TAG"
export FRONTEND_IMAGE="ghcr.io/zcweah1981/demand-hunter-frontend:$TAG"

echo "Deploying $REPO@$SHORT_SHA using images tag '$TAG'"
docker compose pull
docker compose up -d --remove-orphans

echo "Deployed $REPO@$SHORT_SHA with image tag '$TAG'"
