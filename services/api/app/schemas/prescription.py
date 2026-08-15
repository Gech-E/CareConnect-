from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas import CareConnectBase, TimestampSchema

class PrescriptionResponse(TimestampSchema):
    id: UUID = Field(..., description="Prescription ID")
    patient_id: UUID = Field(..., description="Patient ID")
    practitioner_id: UUID = Field(..., description="Practitioner ID")
    prescriber_name: str = Field(..., description="Prescriber name")
    medication: str = Field(..., description="Medication name")
    dosage: str = Field(..., description="Dosage instructions")
    quantity: int = Field(..., description="Quantity to dispense")
    refills_authorized: int = Field(0, description="Number of refills authorized")
    status: str = Field(..., description="Prescription status")
    notes: str | None = Field(None, description="Additional notes")

class FulfillmentOptionResponse(CareConnectBase):
    pharmacy_name: str = Field(..., description="Pharmacy name")
    pharmacy_address: str = Field(..., description="Pharmacy address")
    delivery_methods: list[str] = Field(..., description="Available delivery methods")
    estimated_time: str = Field(..., description="Estimated time for fulfillment")

class FulfillmentRequestCreate(CareConnectBase):
    pharmacy_name: str = Field(..., description="Pharmacy name")
    delivery_method: str = Field(..., description="Selected delivery method")

class FulfillmentRequestResponse(TimestampSchema):
    id: UUID = Field(..., description="Fulfillment request ID")
    prescription_id: UUID = Field(..., description="Prescription ID")
    pharmacy_name: str = Field(..., description="Pharmacy name")
    delivery_method: str = Field(..., description="Delivery method")
    status: str = Field(..., description="Fulfillment status")

class RefillRequestCreate(CareConnectBase):
    notes: str | None = Field(None, description="Additional notes for refill")
