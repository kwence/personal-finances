# FinanceFam — personal finance app

A small but complete personal finance manager built with **Django 5** and **Bootstrap 5**, with a calm light-green theme. Bootstrap and Bootstrap Icons are bundled locally, so the UI works without a CDN.

## Features

- User registration, login and sign out (Django auth, styled forms)
- Dashboard with:
  - net balance, monthly income, monthly expenses and savings rate
  - 6-month income vs expenses chart (pure CSS, no chart library)
  - expense breakdown donut chart and legend
  - recent transactions, budget progress and savings goals
- Transaction tracking: add, edit, delete, filter by type/category/month/text, paginated list
- Categories: income/expense groups with colours and icons
- Monthly budgets per expense category with spent/remaining progress
- Savings goals with one-click contributions
- Currency selector in the top bar: **USD ($)**, **GBP (£)** or **EUR (€)** — the choice is saved to your account and applied to every amount
- Every record is tied to the signed-in user; other users' data is never shown
- Demo seed data and an automated test suite

## Quick start

From this directory (`finance-app/`):

```bash
python3 -m pip install -r requirements.txt      # or: pip install -r requirements.txt
python3 manage.py migrate
python3 manage.py seed_demo                     # optional: sample data for the demo user
python3 manage.py runserver
```

Open <http://127.0.0.1:8000/>.

### Demo account (created by `seed_demo`)

| Field | Value |
| --- | --- |
| Username | `demo` |
| Password | `DemoPass123!` |

The seed command can be re-run at any time: it refreshes only the demo account's data (six months of transactions, categories, budgets and goals). You can also register your own account from the sign-up page — new accounts start empty.

## Tests

```bash
python3 manage.py test finances -v 2
```

The suite covers models, date/total helpers, authentication, dashboard scoping, transaction CRUD and filters, ownership checks, budgets, goals, and the seed command.

## Useful commands

```bash
python3 manage.py createsuperuser                 # admin account
python3 manage.py collectstatic --noinput         # collect static files for deployment
python3 manage.py check                           # system checks
```

## Project layout

```
config/                 # Django project settings and URLs
finances/
  models.py             # Category, Transaction, Budget, Goal
  views.py              # dashboard, auth, CRUD views
  forms.py              # Bootstrap-friendly forms
  utils.py              # date and total helpers
  context_processors.py # current user's currency preference
  templatetags/         # Bootstrap field + money formatting helpers
  templates/            # base layout, auth pages, dashboard, CRUD pages
  static/               # bundled Bootstrap, Bootstrap Icons and theme.css
  management/commands/seed_demo.py
  tests.py
```

## Notes

`settings.py` uses SQLite, `DEBUG = True` and a hard-coded development `SECRET_KEY` so the demo runs with zero configuration. Change those before deploying to production.
