# Worker

The API and Celery use the same locked image and model code. The sole worker
entrypoint is `app.worker:celery_app` in `services/api`:

```sh
celery -A app.worker:celery_app worker --loglevel=info
celery -A app.worker:celery_app beat --loglevel=info --schedule=/tmp/celerybeat-schedule
```

Run one beat scheduler per environment. Hold expiry is transactional and safe to
retry. Notification, reminder and FHIR tasks are explicit local simulations;
they fail when demo providers are disabled until real adapters are implemented.
