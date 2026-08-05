# CareConnect Runbook

## Service Dependencies
- **PostgreSQL**: Primary transactional database. Required for API functionality.
- **Redis**: Caching and background job broker. Required for ARQ worker.
- **MinIO (S3-compatible)**: Encrypted object storage for patient records and attachments.

## Common Operations

### Database Migrations
To create a new migration:
```bash
cd services/api
alembic revision --autogenerate -m "Add new table"
```
To apply migrations:
```bash
alembic upgrade head
```

### Running Tests
Frontend:
```bash
pnpm run test
```
Backend:
```bash
cd services/api
pytest
```

### Troubleshooting
- **API not starting**: Check if PostgreSQL is healthy (`docker-compose ps`). Verify `DATABASE_URL` in `.env`.
- **Worker not processing**: Check Redis connection `REDIS_URL`. View worker logs using `docker logs careconnect-worker-1`.
- **Uploads failing**: Verify MinIO credentials and bucket creation. Ensure `STORAGE_ACCESS_KEY` is correctly mapped.

## Deployment Strategy
Production deployment is driven by GitHub Actions and Terraform modules (located in `infra/terraform`). Staging must pass full E2E automation, security container scanning, and accessibility checks before production rollout.
