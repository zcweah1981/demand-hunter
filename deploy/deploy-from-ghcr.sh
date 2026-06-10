#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/damand-hunter}"
REPO="${REPO:-zcweah1981/demand-hunter}"
VERSION="${1:-v0.1.0}"

mkdir -p "$APP_DIR/shared/data" "$APP_DIR/shared/output" "$APP_DIR/backups"
cd "$APP_DIR"

REF="refs/tags/$VERSION"
SHA="$(git ls-remote "https://github.com/$REPO.git" "$REF" | awk '{print $1}')"
if [[ -z "$SHA" && "$VERSION" == "main" ]]; then
  REF="refs/heads/main"
  SHA="$(git ls-remote "https://github.com/$REPO.git" "$REF" | awk '{print $1}')"
fi
if [[ -z "$SHA" ]]; then
  echo "Cannot resolve $REPO version '$VERSION'. Create/push tag first, e.g. git tag $VERSION && git push origin $VERSION" >&2
  exit 1
fi
SHORT_SHA="${SHA:0:7}"

cp docker-compose.yml "backups/docker-compose.yml.$(date +%Y%m%d-%H%M%S).bak"
sed -i -E "s#ghcr.io/zcweah1981/demand-hunter-backend:[^[:space:]]+#ghcr.io/zcweah1981/demand-hunter-backend:$VERSION#g; s#ghcr.io/zcweah1981/demand-hunter-frontend:[^[:space:]]+#ghcr.io/zcweah1981/demand-hunter-frontend:$VERSION#g" docker-compose.yml

cat > "$APP_DIR/.deploy-version" <<EOF
repo=$REPO
ref=$REF
sha=$SHA
version=$VERSION
deployed_at=$(date -Is)
EOF

echo "Deploying $REPO@$VERSION ($SHORT_SHA)"
docker compose pull
docker compose up -d --remove-orphans

echo "Deployed $REPO@$VERSION ($SHORT_SHA)"
