#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/damand-hunter}"
REPO="${REPO:-zcweah1981/demand-hunter}"
TAG="${1:-latest}"
REF="${2:-main}"

mkdir -p "$APP_DIR/shared/data" "$APP_DIR/shared/output" "$APP_DIR/backups"
cd "$APP_DIR"

if [[ "$REF" == v* ]]; then
  GIT_REF="refs/tags/$REF"
else
  GIT_REF="refs/heads/$REF"
fi
SHA="$(git ls-remote "https://github.com/$REPO.git" "$GIT_REF" | awk '{print $1}')"
if [[ -z "$SHA" ]]; then
  echo "Cannot resolve $REPO ref '$REF'" >&2
  exit 1
fi
SHORT_SHA="${SHA:0:7}"

cp docker-compose.yml "backups/docker-compose.yml.$(date +%Y%m%d-%H%M%S).bak"
sed -i -E "s#ghcr.io/zcweah1981/demand-hunter-backend:[^[:space:]]+#ghcr.io/zcweah1981/demand-hunter-backend:$TAG#g; s#ghcr.io/zcweah1981/demand-hunter-frontend:[^[:space:]]+#ghcr.io/zcweah1981/demand-hunter-frontend:$TAG#g" docker-compose.yml

cat > "$APP_DIR/.deploy-version" <<EOF
repo=$REPO
ref=$REF
sha=$SHA
tag=$TAG
deployed_at=$(date -Is)
EOF

echo "Deploying $REPO ref '$REF' ($SHORT_SHA) using image tag '$TAG'"
docker compose pull
docker compose up -d --remove-orphans

echo "Deployed $REPO@$SHORT_SHA with image tag '$TAG'"
