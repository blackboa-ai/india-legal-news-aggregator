"""
Health response schemas.
"""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """
    Standard health check response model.
    """
    status: str = Field(..., examples=["ok"], description="Service health state")
    service: str = Field(..., examples=["india-legal-aggregator"], description="Unique service identifier")
