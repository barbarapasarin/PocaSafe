# Copilot instructions for PocaSafe

## Project overview
PocaSafe is a Django marketplace for collectible items, centered on a secure escrow flow for sales and dispute mediation. The project is intentionally compact: one Django project (`pocasafe_core`) and one app (`marketplace`).

- Project config and global settings live in `pocasafe_core/settings.py` and `pocasafe_core/urls.py`.
- Most domain logic lives in `marketplace/models.py`, `marketplace/views.py`, and `marketplace/forms.py`.
- HTML UI lives under `templates/marketplace/`.
- Database migrations live under `marketplace/migrations/`.
- Build/bootstrap script is `build.sh`.

## Setup and commands
Use the repo's existing Django flow rather than inventing a custom runner.

### Install dependencies
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Local bootstrap / app startup
```bash
python manage.py migrate
python manage.py runserver
```

### Validation checks
```bash
python manage.py check
```

### Test commands
There is no dedicated pytest/ruff configuration in this repo; the default project validation is the Django test runner.

```bash
# Run the full Django test suite
python manage.py test

# Run the app-level suite
python manage.py test marketplace

# Run a specific module or class when tests are added
python manage.py test marketplace.tests
```

### Build/deploy script
The repo includes `build.sh`, which does the expected deployment bootstrap:

```bash
./build.sh
```

This script installs requirements, runs `collectstatic`, and applies migrations.

## Architecture notes
### Django project structure
- `pocasafe_core/settings.py` configures the project, database selection, auth redirects, Cloudinary storage, and WhiteNoise static serving.
- `pocasafe_core/urls.py` mounts the marketplace app at the site root and exposes the admin interface.
- `marketplace/urls.py` defines the user-facing routes for listing items, checkout, order tracking, disputes, and authentication.

### Core domain model
`marketplace/models.py` contains the main business entities:

- `Profile`: extends Django user accounts with seller metadata.
- `CollectibleItem`: collectible listings with status (`available`, `in_escrow`, `sold`) and category choices.
- `Order`: escrow/payment state machine for purchase flows and disputes.
- `Review`: user feedback that recalculates the reviewed user's aggregate reputation.

### Request flow
The app follows a straightforward Django MVC pattern:

- `views.py` handles catalog browsing, registration, item publishing, purchases, delivery confirmation, and admin dispute resolution.
- `forms.py` contains the registration, item creation, and order forms.
- Templates under `templates/marketplace/` render the user pages and admin flows.

### Escrow/dispute workflow
This project's biggest business logic is the escrow and mediation flow. Preserve the existing state transitions when editing code:

- `CollectibleItem.status` and `Order.status` are explicitly coded as strings.
- Checkout uses `transaction.atomic()` and `select_for_update()` to prevent duplicate purchases of the same item.
- Order progression includes `paid_escrow`, `shipped`, `delivered`, `disputed`, and `cancelled` states.
- The dispute dashboard and resolution endpoints are restricted to `@staff_member_required` users.

## Key conventions and repo-specific patterns
- Keep routes and view names aligned with the names declared in `marketplace/urls.py` (`item_list`, `item_detail`, `buy_item`, `dispute_dashboard`, etc.).
- Preserve the explicit Spanish-language status strings and admin messages already used in the app; changing them without updating templates or expectations is likely to break workflow assumptions.
- When changing order or escrow logic, update both the `Order` and related `CollectibleItem` state together in the same transaction.
- Do not add ad hoc local storage or file paths for media; the project is configured for Cloudinary-backed media and WhiteNoise static files.
- Auth-related defaults are configured in `pocasafe_core/settings.py` (`LOGIN_URL`, `LOGIN_REDIRECT_URL`, `LOGOUT_REDIRECT_URL`).
- The project is single-app and uses Django's built-in auth system (`django.contrib.auth`), not a custom auth backend.

## Environment and deployment notes
- Database selection is environment-driven: `DATABASE_URL` activates PostgreSQL-compatible configuration; otherwise the project falls back to SQLite.
- Cloudinary credentials come from environment variables (`CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`) with defaults placeholders in `settings.py`.
- `ALLOWED_HOSTS` is intentionally broad for deployment flexibility.

## Working safely in this repo
- Prefer editing within the existing Django app structure rather than introducing new frameworks or service layers.
- Use `python manage.py check` after significant model/view/form changes.
- If you add new functionality that affects inventory or escrow, validate the relevant flow with a focused Django test or a `manage.py check` pass.
