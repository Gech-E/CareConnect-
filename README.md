# CareConnect Telehealth Platform

CareConnect is a patient-centered telehealth platform designed to enable secure virtual care, record access, secure messaging, and prescription management.

## Architecture
This project is built using a modern monorepo structure:
- **apps/patient-mobile**: React Native + Expo + TypeScript
- **apps/clinician-web**: Next.js + TypeScript + Tailwind CSS
- **apps/admin-web**: Next.js + TypeScript + Tailwind CSS
- **services/api**: FastAPI + Pydantic + SQLAlchemy (Python)
- **services/worker**: ARQ + Redis (Python)
- **infra**: Docker Compose local development setup

## Requirements
- Node.js >= 20
- pnpm >= 8
- Python >= 3.11
- Docker & Docker Compose

## Quick Start (Local Development)

1. Start the infrastructure (PostgreSQL, Redis, MinIO):
   ```bash
   docker-compose -f infra/docker-compose.yml up -d
   ```

2. Install frontend dependencies:
   ```bash
   pnpm install
   ```

3. Setup backend dependencies (in another terminal):
   ```bash
   cd services/api
   pip install -e .[dev]
   alembic upgrade head
   ```

4. Run all frontend apps via Turborepo:
   ```bash
   pnpm run dev
   ```

5. Run the FastAPI backend:
   ```bash
   cd services/api
   uvicorn app.main:app --reload
   ```

## Security & Compliance
- **Synthetic Data**: By design, all local setups and mocks use exclusively synthetic data. Do not place real PHI or secrets in code, logs, or UI.
- **RBAC**: Server-side role-based access control is enforced on all APIs.
- **Auditing**: All data access and mutations are logged in the `Audit` table.
- **Accessibility**: UI follows WCAG 2.2 AA standards.
