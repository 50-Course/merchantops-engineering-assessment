#!/usr/bin/env bash
set -euo pipefail

echo "Starting MerchantOps database and backend..."
docker compose up -d --build db backend

echo "Applying database migrations..."
docker compose exec -T backend python manage.py migrate --noinput

echo "Preparing assessment catalogue..."
docker compose exec -T backend python manage.py seed_catalog --products 5000 --seed 42

echo "Preparing complex product fixtures..."
docker compose exec -T backend python manage.py seed_complex_products

echo "Provisioning demo operator..."
docker compose exec backend python manage.py provision_demo_user

echo "Resolving Northstar Retail merchant ID..."
merchant_id="$(
  docker compose exec -T backend python -c '
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()
from catalog.models import Merchant
print(Merchant.objects.get(slug="assessment-merchant-01").pk)
' | tr -d '\r\n'
)"

if ! [[ "$merchant_id" =~ ^[0-9]+$ ]]; then
  echo "Could not resolve merchant ID." >&2
  exit 1
fi

printf 'VITE_MERCHANT_ID=%s\nVITE_MERCHANT_NAME=Northstar Retail\n'   "$merchant_id" > frontend/.env.local

echo "Configured frontend for merchant ID $merchant_id."

echo "Starting frontend..."
docker compose up -d --force-recreate --no-deps frontend

echo
echo "MerchantOps is ready."
frontend_port="${MERCHANTOPS_FRONTEND_PORT:-5173}"
echo "Frontend: http://127.0.0.1:${frontend_port}/"
echo "Username: demo_operator"
