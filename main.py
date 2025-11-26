"""
Main FastAPI application for LLM Quiz Analysis
Handles incoming quiz requests and orchestrates the quiz-solving process
"""
import os
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv
import logging

from quiz_agent import QuizAgent

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="LLM Quiz Analysis API",
    description="API endpoint for solving LLM-based quiz tasks",
    version="1.0.0"
)

# Load configuration from environment
EXPECTED_SECRET = os.getenv("QUIZ_SECRET", "")
STUDENT_EMAIL = os.getenv("STUDENT_EMAIL", "")

if not EXPECTED_SECRET:
    logger.warning("QUIZ_SECRET not set in environment variables")
if not STUDENT_EMAIL:
    logger.warning("STUDENT_EMAIL not set in environment variables")


class QuizRequest(BaseModel):
    """Request model for quiz endpoint"""
    email: str
    secret: str
    url: str = Field(..., description="Quiz URL to solve")

    # Allow extra fields that might be sent
    model_config = {"extra": "allow"}

    @classmethod
    @field_validator('email')
    def validate_email(cls, v: str) -> str:
        """Simple email validation - check for @ symbol"""
        if '@' not in v:
            raise ValueError('Invalid email format - must contain @')
        return v

    @classmethod
    @field_validator('url')
    def validate_url(cls, v: str) -> str:
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v


class QuizResponse(BaseModel):
    """Response model for quiz endpoint"""
    status: str
    message: str
    started_at: str
    email: str


# Global quiz agent instance
quiz_agent: Optional[QuizAgent] = None


@app.on_event("startup")
async def startup_event():
    """Initialize quiz agent on startup"""
    global quiz_agent
    try:
        quiz_agent = QuizAgent()
        logger.info("Quiz agent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize quiz agent: {str(e)}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down application")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "LLM Quiz Analysis API",
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "quiz_agent_initialized": quiz_agent is not None,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/quiz", response_model=QuizResponse)
async def handle_quiz(request: QuizRequest):
    """
    Main endpoint to receive and process quiz requests

    - Validates secret and email
    - Starts async quiz-solving process
    - Returns immediate response while processing continues
    """
    try:
        # Validate secret
        if request.secret != EXPECTED_SECRET:
            logger.warning(f"Invalid secret attempt from {request.email}")
            raise HTTPException(
                status_code=403,
                detail="Invalid secret. Access denied."
            )

        # Validate email (optional check)
        if STUDENT_EMAIL and request.email != STUDENT_EMAIL:
            logger.warning(f"Email mismatch: expected {STUDENT_EMAIL}, got {request.email}")

        # Start quiz solving in background
        logger.info(f"Received quiz request for URL: {request.url}")

        if quiz_agent is None:
            raise HTTPException(
                status_code=500,
                detail="Quiz agent not initialized"
            )

        # Start async quiz solving (fire and forget)
        asyncio.create_task(
            quiz_agent.solve_quiz_chain(
                email=request.email,
                secret=request.secret,
                start_url=request.url
            )
        )

        # Return immediate response
        return QuizResponse(
            status="accepted",
            message="Quiz solving process started",
            started_at=datetime.utcnow().isoformat(),
            email=request.email
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling quiz request: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle validation errors"""
    logger.error(f"Validation error: {str(exc)}")
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors"""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn

    # Get port from environment or use default
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info(f"Starting server on {host}:{port}")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
