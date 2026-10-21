# Savannah Clinic Booking API

A Django REST Framework API for a small clinic where doctors offer 30-minute appointments. The API uses SQLite locally and can be switched to PostgreSQL for production through Django's normal database configuration.

## System design

**Models.** `Doctor` stores a name and one weekly work schedule (weekday, start, end). `Patient` stores patient identity. `Appointment` joins a patient to a doctor and a timezone-aware start time, with a `booked` or `cancelled` state and cancellation reason.

**Availability.** Slots are generated at read time from a doctor's configured schedule, in 30-minute increments. Active appointments are subtracted. This avoids pre-populating a large, hard-to-maintain slot table while keeping the rules in one service.

**Concurrency.** A conditional database unique constraint on `(doctor, starts_at)` for booked appointments is the final guard against two requests claiming one slot. Creation and rescheduling use transactions and translate races into useful validation errors. Cancelled appointments do not participate in that constraint, so the time becomes available again.

**Trade-offs.** This deliberately models one recurring weekly schedule per doctor, adequate for the brief. Production would introduce `DoctorSchedule` and exceptions/leave records. SQLite is simple for evaluation; PostgreSQL is recommended in production for stronger concurrent-write behavior.

## API

All datetimes are ISO-8601 with a timezone, for example `2026-10-20T09:00:00+03:00`.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/appointments` | Book a doctor/patient/starts_at slot |
| GET | `/doctors/{id}/availability?date=YYYY-MM-DD` | List available slots |
| PATCH | `/appointments/{id}/cancel` | Cancel with `{ "reason": "..." }` |
| PATCH | `/appointments/{id}/reschedule` | Change with `{ "starts_at": "..." }` |
| GET | `/patients/{id}/appointments` | Bonus: upcoming booked appointments |

Bookings must be on a 30-minute boundary, during the assigned doctor's working day/hours, at least one hour ahead, and unclaimed. The API responds with DRF validation errors (400), missing-resource errors (404), and a 409 for repeat cancellation.

## Run locally

```bash
python -m venv .venv
.venv\\Scripts\\activate  # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser  # optional; use /admin to add doctors and patients
python manage.py runserver
python manage.py test
```

## Deployment and CI/CD

The supplied GitHub Actions workflow runs tests for every pull request. A successful push to `main` (the designated deployment branch) invokes Render's deploy hook stored as `RENDER_DEPLOY_HOOK_URL` in GitHub Actions secrets. On Render, configure Build Command `pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput` and Start Command `gunicorn clinic_project.wsgi:application`. Set `DJANGO_SECRET_KEY`, `DEBUG=False`, and `ALLOWED_HOSTS` there. Add the eventual public deployment URL here before submission.

## AI reflection

1. I used AI to accelerate the initial project scaffold, endpoint mapping, README draft, and test-case brainstorming; I reviewed and adapted all output.
2. Prompt: “Design a robust Django booking flow that prevents concurrent claims of a doctor/time slot.” The suggestion to combine an application transaction with a conditional database constraint improved the design beyond an application-only availability check.
3. An early generated test assumed every future timestamp with `minute=0` was in working hours. I caught that while reviewing the fixture and made it advance to a valid doctor working day and time. This illustrates why generated tests need review.
4. I independently chose a read-time generated availability list rather than materialized slots, because the clinic is small and appointments are the source of truth. I also chose to require an explicit timezone in API datetimes to avoid silently booking at the wrong local time.
