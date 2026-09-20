# Budget & Expenditure Approval App

A responsive web app (works on desktop and mobile browsers — no separate app
install needed) for tracking expenditure, approving budgets against uploaded
vendor quotations, and releasing payments against already-approved budgets,
with reporting by category.

## How it works

**Roles** (set per user under Admin → Users & Roles, or in Django Admin):

- **Requester** — creates budget requests (with a quotation) and payment requests.
- **Approver 1** — first-level sign-off on both budget requests and payments.
- **Approver 2** — final sign-off; approving a budget request locks in the
  approved amount (which can be adjusted down/up from the quoted amount).
- **Administrator** — manages categories and users, and can see/do everything
  the other roles can.

**Workflow:**

1. A Requester creates a **Budget Request**: category, title, vendor, quoted
   amount, and an optional quotation file upload.
2. **Approver 1** reviews and approves or rejects it.
3. **Approver 2** gives the final approval (optionally adjusting the approved
   amount), which sets the item's official **Approved Budget**.
4. Once approved, a Requester can raise a **Payment** against that budget
   item. The amount is validated against the remaining approved balance so
   it's impossible to overpay a budget.
5. Payments go through the same Approver 1 → Approver 2 sign-off before being
   marked as released, at which point they count as "utilized" against the
   category.
6. **Reports** (Reports menu) show Approved Budget vs Utilized by category
   (with a chart) and a per-item Approved vs Spent breakdown. The Dashboard
   gives an at-a-glance summary and highlights anything waiting on your
   approval.

A rejected budget request can be resubmitted by its requester for a fresh
approval cycle.

## Running it locally

Requires Python 3.11+.

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # then edit if needed
python manage.py migrate
python manage.py seed_data       # creates starter categories + demo users
python manage.py runserver
```

Open http://127.0.0.1:8000 — you'll be redirected to the login page.

**Demo accounts created by `seed_data`** (change these before real use):

| Username | Role | Password |
|---|---|---|
| admin | Administrator | ChangeMe123! |
| requester1 | Requester | ChangeMe123! |
| approver1 | Approver 1 | ChangeMe123! |
| approver2 | Approver 2 | ChangeMe123! |

To skip the demo users and only get the starter categories, run
`python manage.py seed_data --no-demo-users`.

To create a proper superuser instead: `python manage.py createsuperuser`
(then set their role to Administrator from Admin → Users & Roles, or Django
Admin → Profiles).

## Managing users day to day

Log in as an Administrator and go to **Admin → Users & Roles** to create
accounts, assign roles, reset passwords, or deactivate someone — no coding
needed. The same is also available via Django's built-in admin at `/admin/`.

## Managing categories

**Admin → Categories** lets you add/rename/deactivate expenditure categories
(e.g. Materials & Equipment, Subcontractor & Services, Travel, etc.) at any
time. Deactivating a category hides it from new requests without deleting its
history.

## Deploying (Render)

This project is set up the same way as your other Django apps (VDRL, ITP,
calibration): Gunicorn + Whitenoise for static files + Postgres via
`DATABASE_URL`.

1. Push this project to a Git repository (GitHub/GitLab).
2. In Render, choose **New → Blueprint** and point it at the repo — it will
   read `render.yaml` and provision both the web service and a free Postgres
   database automatically. (Alternatively create a Web Service manually with
   build command `pip install -r requirements.txt && python manage.py collectstatic --noinput`
   and start command `gunicorn config.wsgi:application`, then add a Postgres
   database and copy its connection string into a `DATABASE_URL` env var.)
3. Once deployed, open a shell on the Render service (or run once locally
   against the production `DATABASE_URL`) and run:
   ```bash
   python manage.py migrate
   python manage.py seed_data
   python manage.py createsuperuser
   ```
4. Log in and immediately change the demo passwords (or delete the demo
   users) from **Admin → Users & Roles**.

Uploaded quotations and payment proofs are stored on local disk
(`MEDIA_ROOT`) by default. Render's free-tier disk is **not persistent**
across deploys — for production use, plan to point `quotation_file` /
`proof_file` storage at S3-compatible object storage (e.g. via
`django-storages`) once you're ready to go live; ask if you'd like this wired
up.

## Project layout

```
config/          Django project settings/urls
accounts/        Login, user & role management (Profile model with role field)
expenditure/     Categories, BudgetRequest, Payment models, views, reports
templates/       Bootstrap 5 responsive templates (desktop + mobile)
```

## Notes on scope / what to extend next

- Currency is fixed at AED app-wide via the `CURRENCY_CODE` setting/env var —
  change it in `.env` if you need a different default currency.
- Categories ship with a starter list (Materials & Equipment, Subcontractor &
  Services, Travel & Accommodation, Office & Admin, Utilities & Facilities,
  Miscellaneous) — edit freely from Admin → Categories.
- Approver assignment is role-based (any Approver 1 can act on any pending
  item at that stage) rather than per-category. If you later want specific
  approvers tied to specific categories or amount thresholds, that's a
  natural next step to add.
- Everything is single-currency; multi-currency conversion isn't handled.
