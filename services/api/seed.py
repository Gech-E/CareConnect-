"""Synthetic seed data for CareConnect Telehealth.

Per SRS: All data is synthetic. No real PHI.
Personas: Maya Johnson (patient), Dr. Daniel Bekele (clinician),
Helen Brooks (admin).
"""

import asyncio
from datetime import UTC, date, datetime, time, timedelta
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core import get_settings
from app.core.security import hash_password

# Import all models to ensure they are registered with SQLAlchemy
from app.models.user import User, UserSession
from app.models.patient import PatientProfile, InsurancePolicy
from app.models.practitioner import Practitioner, PractitionerRole, Organization
from app.models.availability import AvailabilityRule, AvailabilityException
from app.models.appointment import Appointment, AppointmentStatusHistory
from app.models.encounter import Encounter, VideoSession
from app.models.consent import Consent
from app.models.messaging import MessageThread, MessageThreadParticipant, Message
from app.models.record import MedicalRecord, Document
from app.models.prescription import Prescription, FulfillmentRequest
from app.models.notification import Notification
from app.models.audit import AuditEvent
from app.models.support import SupportCase

settings = get_settings()


async def seed_database():
    """Populate the database with synthetic data for development."""
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        # Check if already seeded
        result = await db.execute(text("SELECT COUNT(*) FROM users"))
        count = result.scalar()
        if count and count > 0:
            print("Database already seeded. Skipping.")
            await engine.dispose()
            return

        print("Seeding CareConnect database with synthetic data...")

        # ── Users ────────────────────────────────────────────────
        from app.models.user import User

        # Patient: Maya Johnson (PRD §4.1)
        patient_id = uuid4()
        patient = User(
            id=patient_id,
            email="maya.johnson@example.com",
            password_hash=hash_password("Patient123!"),
            role="patient",
            is_active=True,
            is_verified=True,
        )

        # Additional patients
        patient2_id = uuid4()
        patient2 = User(
            id=patient2_id,
            email="james.wilson@example.com",
            password_hash=hash_password("Patient123!"),
            role="patient",
            is_active=True,
            is_verified=True,
        )

        patient3_id = uuid4()
        patient3 = User(
            id=patient3_id,
            email="sarah.martinez@example.com",
            password_hash=hash_password("Patient123!"),
            role="patient",
            is_active=True,
            is_verified=True,
        )

        # Clinician: Dr. Daniel Bekele (PRD §4.2)
        clinician_user_id = uuid4()
        clinician_user = User(
            id=clinician_user_id,
            email="dr.bekele@careconnect.health",
            password_hash=hash_password("Clinician123!"),
            role="clinician",
            is_active=True,
            is_verified=True,
        )

        # Additional clinicians
        clinician2_user_id = uuid4()
        clinician2_user = User(
            id=clinician2_user_id,
            email="dr.chen@careconnect.health",
            password_hash=hash_password("Clinician123!"),
            role="clinician",
            is_active=True,
            is_verified=True,
        )

        clinician3_user_id = uuid4()
        clinician3_user = User(
            id=clinician3_user_id,
            email="dr.patel@careconnect.health",
            password_hash=hash_password("Clinician123!"),
            role="clinician",
            is_active=True,
            is_verified=True,
        )

        clinician4_user_id = uuid4()
        clinician4_user = User(
            id=clinician4_user_id,
            email="dr.thompson@careconnect.health",
            password_hash=hash_password("Clinician123!"),
            role="clinician",
            is_active=True,
            is_verified=True,
        )

        # Admin: Helen Brooks (PRD §4.3)
        admin_id = uuid4()
        admin_user = User(
            id=admin_id,
            email="helen.brooks@careconnect.health",
            password_hash=hash_password("Admin123!"),
            role="admin",
            is_active=True,
            is_verified=True,
        )

        # Support agent
        support_id = uuid4()
        support_user = User(
            id=support_id,
            email="support@careconnect.health",
            password_hash=hash_password("Support123!"),
            role="support",
            is_active=True,
            is_verified=True,
        )

        db.add_all([
            patient, patient2, patient3,
            clinician_user, clinician2_user, clinician3_user, clinician4_user,
            admin_user, support_user,
        ])
        await db.flush()

        # ── Patient Profiles ─────────────────────────────────────
        from app.models.patient import PatientProfile, InsurancePolicy

        profile1 = PatientProfile(
            user_id=patient_id,
            legal_first_name="Maya",
            legal_last_name="Johnson",
            date_of_birth=date(1990, 3, 15),
            gender="female",
            address_line1="456 Oak Avenue",
            city="San Francisco",
            state="CA",
            zip_code="94102",
            country="US",
            timezone="America/Los_Angeles",
            preferred_language="en",
            emergency_contact_name="Robert Johnson",
            emergency_contact_phone="+14155551234",
            communication_pref_email=True,
            communication_pref_sms=True,
            communication_pref_push=True,
        )

        profile2 = PatientProfile(
            user_id=patient2_id,
            legal_first_name="James",
            legal_last_name="Wilson",
            date_of_birth=date(1985, 7, 22),
            gender="male",
            address_line1="789 Pine Street",
            city="New York",
            state="NY",
            zip_code="10001",
            country="US",
            timezone="America/New_York",
            preferred_language="en",
            emergency_contact_name="Emily Wilson",
            emergency_contact_phone="+12125559876",
            communication_pref_email=True,
            communication_pref_sms=False,
            communication_pref_push=True,
        )

        profile3 = PatientProfile(
            user_id=patient3_id,
            legal_first_name="Sarah",
            legal_last_name="Martinez",
            date_of_birth=date(1995, 11, 8),
            gender="female",
            address_line1="321 Elm Drive",
            city="Austin",
            state="TX",
            zip_code="73301",
            country="US",
            timezone="America/Chicago",
            preferred_language="es",
            emergency_contact_name="Carlos Martinez",
            emergency_contact_phone="+15125554321",
            communication_pref_email=True,
            communication_pref_sms=True,
            communication_pref_push=False,
        )

        db.add_all([profile1, profile2, profile3])

        # Insurance
        insurance1 = InsurancePolicy(
            patient_id=patient_id,
            payer_name="Blue Cross Blue Shield",
            member_id="BCB-123456789",
            group_number="GRP-001",
            plan_name="PPO Gold",
            verification_status="verified",
        )
        db.add(insurance1)

        # ── Organization ─────────────────────────────────────────
        from app.models.practitioner import Organization, Practitioner, PractitionerRole

        org_id = uuid4()
        org = Organization(
            id=org_id,
            name="CareConnect Health Network",
            type="health_system",
            is_active=True,
        )
        db.add(org)
        await db.flush()

        # ── Practitioners ────────────────────────────────────────
        prac1_id = uuid4()
        prac1 = Practitioner(
            id=prac1_id,
            user_id=clinician_user_id,
            first_name="Daniel",
            last_name="Bekele",
            credentials="MD, FACP",
            bio="Board-certified internist with 15 years of experience in primary care and preventive medicine. Passionate about patient-centered virtual care.",
            years_of_experience=15,
            status="active",
            average_rating=4.8,
            review_count=127,
        )

        prac2_id = uuid4()
        prac2 = Practitioner(
            id=prac2_id,
            user_id=clinician2_user_id,
            first_name="Emily",
            last_name="Chen",
            credentials="MD, Board Certified Dermatologist",
            bio="Dermatology specialist focusing on teledermatology. Expert in skin conditions, acne management, and preventive skin care.",
            years_of_experience=10,
            status="active",
            average_rating=4.9,
            review_count=89,
        )

        prac3_id = uuid4()
        prac3 = Practitioner(
            id=prac3_id,
            user_id=clinician3_user_id,
            first_name="Raj",
            last_name="Patel",
            credentials="MD, Psychiatrist",
            bio="Board-certified psychiatrist specializing in anxiety, depression, and stress management through telehealth.",
            years_of_experience=12,
            status="active",
            average_rating=4.7,
            review_count=156,
        )

        prac4_id = uuid4()
        prac4 = Practitioner(
            id=prac4_id,
            user_id=clinician4_user_id,
            first_name="Lisa",
            last_name="Thompson",
            credentials="NP, Family Nurse Practitioner",
            bio="Family nurse practitioner with expertise in women's health, chronic disease management, and wellness consultations.",
            years_of_experience=8,
            status="active",
            average_rating=4.6,
            review_count=73,
        )

        db.add_all([prac1, prac2, prac3, prac4])
        await db.flush()

        # ── Practitioner Roles ───────────────────────────────────
        role1 = PractitionerRole(
            practitioner_id=prac1_id,
            organization_id=org_id,
            specialty="Internal Medicine",
            languages=["en", "am"],
            service_areas=["CA", "NY", "TX"],
            visit_types=["video", "audio"],
            price_range_min=75.00,
            price_range_max=150.00,
        )

        role2 = PractitionerRole(
            practitioner_id=prac2_id,
            organization_id=org_id,
            specialty="Dermatology",
            languages=["en", "zh"],
            service_areas=["CA", "WA", "OR"],
            visit_types=["video"],
            price_range_min=100.00,
            price_range_max=200.00,
        )

        role3 = PractitionerRole(
            practitioner_id=prac3_id,
            organization_id=org_id,
            specialty="Psychiatry",
            languages=["en", "hi"],
            service_areas=["CA", "NY", "TX", "FL"],
            visit_types=["video", "audio"],
            price_range_min=125.00,
            price_range_max=250.00,
        )

        role4 = PractitionerRole(
            practitioner_id=prac4_id,
            organization_id=org_id,
            specialty="Family Medicine",
            languages=["en", "es"],
            service_areas=["TX", "NM", "AZ"],
            visit_types=["video", "audio"],
            price_range_min=60.00,
            price_range_max=120.00,
        )

        db.add_all([role1, role2, role3, role4])

        # ── Availability Rules ───────────────────────────────────
        from app.models.availability import AvailabilityRule

        for prac_id in [prac1_id, prac2_id, prac3_id, prac4_id]:
            for day in range(0, 5):  # Monday-Friday
                rule = AvailabilityRule(
                    practitioner_id=prac_id,
                    day_of_week=day,
                    start_time=time(9, 0),
                    end_time=time(17, 0),
                    visit_duration_minutes=30,
                    buffer_minutes=10,
                    timezone="America/Los_Angeles",
                    is_active=True,
                )
                db.add(rule)

        # ── Sample Appointments ──────────────────────────────────
        from app.models.appointment import Appointment

        now = datetime.now(UTC)

        # Upcoming appointment
        apt1 = Appointment(
            patient_id=patient_id,
            practitioner_id=prac1_id,
            visit_type="video",
            status="confirmed",
            scheduled_start=now + timedelta(days=2, hours=3),
            scheduled_end=now + timedelta(days=2, hours=3, minutes=30),
            timezone="America/Los_Angeles",
            estimated_price=100.00,
            preparation_instructions="Please have your medication list ready.",
        )

        # Past completed appointment
        apt2 = Appointment(
            patient_id=patient_id,
            practitioner_id=prac2_id,
            visit_type="video",
            status="completed",
            scheduled_start=now - timedelta(days=7),
            scheduled_end=now - timedelta(days=7) + timedelta(minutes=30),
            timezone="America/Los_Angeles",
            estimated_price=150.00,
        )

        # Another patient's appointment
        apt3 = Appointment(
            patient_id=patient2_id,
            practitioner_id=prac3_id,
            visit_type="audio",
            status="confirmed",
            scheduled_start=now + timedelta(days=1, hours=5),
            scheduled_end=now + timedelta(days=1, hours=5, minutes=30),
            timezone="America/New_York",
            estimated_price=175.00,
        )

        db.add_all([apt1, apt2, apt3])
        await db.flush()

        # ── Sample Prescriptions ─────────────────────────────────
        from app.models.prescription import Prescription

        rx1 = Prescription(
            patient_id=patient_id,
            prescriber_id=prac1_id,
            medication_name="Amoxicillin",
            strength="500mg",
            form="capsule",
            quantity="30",
            instructions="Take one capsule three times daily with food for 10 days. Complete the full course even if you feel better.",
            refills_total=0,
            refills_remaining=0,
            status="active",
            prescribed_at=now - timedelta(days=3),
            expires_at=now + timedelta(days=180),
            is_controlled=False,
            source_system="careconnect",
        )

        rx2 = Prescription(
            patient_id=patient_id,
            prescriber_id=prac2_id,
            medication_name="Tretinoin Cream",
            strength="0.025%",
            form="topical cream",
            quantity="1",
            instructions="Apply a thin layer to affected area at bedtime. Avoid sun exposure. Use sunscreen daily.",
            refills_total=3,
            refills_remaining=2,
            status="active",
            prescribed_at=now - timedelta(days=14),
            expires_at=now + timedelta(days=365),
            is_controlled=False,
            source_system="careconnect",
        )

        db.add_all([rx1, rx2])

        # ── Sample Medical Records ───────────────────────────────
        from app.models.record import MedicalRecord

        rec1 = MedicalRecord(
            patient_id=patient_id,
            record_type="clinical_note",
            title="Annual Physical Examination",
            source_system="careconnect",
            service_date=now - timedelta(days=7),
            status="available",
            fhir_resource_type="DiagnosticReport",
        )

        rec2 = MedicalRecord(
            patient_id=patient_id,
            record_type="lab_result",
            title="Complete Blood Count (CBC)",
            source_system="labcorp_mock",
            service_date=now - timedelta(days=14),
            status="available",
            fhir_resource_type="DiagnosticReport",
        )

        rec3 = MedicalRecord(
            patient_id=patient_id,
            record_type="lab_result",
            title="Comprehensive Metabolic Panel",
            source_system="labcorp_mock",
            service_date=now - timedelta(days=14),
            status="available",
            fhir_resource_type="DiagnosticReport",
        )

        db.add_all([rec1, rec2, rec3])

        # ── Sample Consents ──────────────────────────────────────
        from app.models.consent import Consent

        consent1 = Consent(
            patient_id=patient_id,
            consent_type="terms",
            version="1.0",
            status="accepted",
            accepted_at=now - timedelta(days=30),
        )

        consent2 = Consent(
            patient_id=patient_id,
            consent_type="privacy",
            version="1.0",
            status="accepted",
            accepted_at=now - timedelta(days=30),
        )

        consent3 = Consent(
            patient_id=patient_id,
            consent_type="telehealth",
            version="1.0",
            status="accepted",
            accepted_at=now - timedelta(days=30),
        )

        db.add_all([consent1, consent2, consent3])

        # ── Sample Message Thread ────────────────────────────────
        from app.models.messaging import Message, MessageThread, MessageThreadParticipant

        thread = MessageThread(
            appointment_id=apt2.id,
            subject="Follow-up: Annual Physical",
            status="active",
        )
        db.add(thread)
        await db.flush()

        tp1 = MessageThreadParticipant(
            thread_id=thread.id,
            user_id=patient_id,
            role="patient",
        )
        tp2 = MessageThreadParticipant(
            thread_id=thread.id,
            user_id=clinician_user_id,
            role="clinician",
        )
        db.add_all([tp1, tp2])
        await db.flush()

        msg1 = Message(
            thread_id=thread.id,
            sender_id=clinician_user_id,
            body="Hi Maya, your lab results look good overall. Your CBC and metabolic panel are within normal ranges. Keep up the healthy lifestyle!",
            status="read",
            read_at=now - timedelta(days=5),
        )

        msg2 = Message(
            thread_id=thread.id,
            sender_id=patient_id,
            body="Thank you, Dr. Bekele! Should I schedule a follow-up appointment?",
            status="read",
            read_at=now - timedelta(days=4),
        )

        msg3 = Message(
            thread_id=thread.id,
            sender_id=clinician_user_id,
            body="A follow-up in 6 months would be ideal. You can book directly through the app at your convenience.",
            status="delivered",
        )

        db.add_all([msg1, msg2, msg3])

        await db.commit()
        print("✅ Database seeded successfully with synthetic data!")
        print(f"   Patients: maya.johnson@example.com / Patient123!")
        print(f"   Clinician: dr.bekele@careconnect.health / Clinician123!")
        print(f"   Admin: helen.brooks@careconnect.health / Admin123!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_database())
