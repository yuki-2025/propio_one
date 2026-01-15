"""
Pydantic Models / Schemas
"""
from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str
    user_id: str = "1"
    thread_id: str | None = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "How many ticket cases are open now?",
                "user_id": "1",
                "thread_id": None
            }
        }


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str
    thread_id: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "response": "There are currently 42 open ticket cases.",
                "thread_id": "abc123"
            }
        }


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    agent_initialized: bool

