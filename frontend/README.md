# MerchantOps frontend

Run the application from the repository root with `docker compose up -d`.
Open http://127.0.0.1:5173/ and sign in using the provisioned Django account.
Vite proxies API, login, and logout requests to Django. Keep the browser on the
frontend origin for session cookies and CSRF protection.

The default workspace is Northstar Retail (merchant ID 3). Set
`VITE_MERCHANT_ID` and `VITE_MERCHANT_NAME` in the frontend Vite environment
to use another merchant. The signed-in account needs membership in Django.

## Routes

- `/` shows the catalogue with server-side search and pagination.
- `/products/:id` opens the editor. The optional `tab` query selects Pricing,
  Inventory, or Availability.
- `/products/:id/activity` shows the product's paginated audit history.

## Editor limits

The General tab saves name, SKU, description, status, and image path. Category
is read-only because the API does not expose a merchant category list. The
catalogue and editor use local WebP assets in `frontend/public/product-images/`
when the saved path matches `/product-images/<file>.webp`. Both show the
placeholder if the path is empty or the image fails to load.

Pricing, inventory, and availability are read-only. Available inventory is
calculated as quantity minus reservations for each variant.

Build with `docker compose exec frontend npm run build`.
