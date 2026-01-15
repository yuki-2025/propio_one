"""
Chat Router - API endpoints for chat functionality
"""
import logging
import uuid
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..models import ChatRequest, ChatResponse
from ..services import Context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])

# Reference to the agent (will be set in main.py)
_agent = None


def set_agent(agent):
    """Set the agent reference from main app."""
    global _agent
    _agent = agent


def get_agent():
    """Get the agent reference."""
    if _agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    return _agent


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the agent and get a response.
    
    - **message**: The user's message
    - **user_id**: User ID for context (default: "1")
    - **thread_id**: Optional thread ID for conversation continuity (auto-generated if not provided)
    """
    logger.info(f"Chat request received: message='{request.message[:50]}...', user_id={request.user_id}")
    agent = get_agent()
    
    # Generate or use provided thread_id
    thread_id = request.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    logger.debug(f"Using thread_id: {thread_id}")
    
    try:
        response = agent.invoke(
            {"messages": [{"role": "user", "content": request.message}]},
            config=config,
            context=Context(user_id=request.user_id)
        )
        
        # Get the last AI message from the response
        messages = response.get('messages', [])
        ai_response = ""
        for msg in reversed(messages):
            if hasattr(msg, 'type') and msg.type == 'ai' and msg.content:
                ai_response = msg.content
                break
            elif hasattr(msg, 'role') and msg.role == 'assistant' and msg.content:
                ai_response = msg.content
                break
        
        return ChatResponse(
            response=ai_response,
            thread_id=thread_id
        )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    Stream responses from the agent.
    
    Returns a Server-Sent Events (SSE) stream with agent messages.
    """
    logger.info(f"Stream request received: message='{request.message[:50]}...', user_id={request.user_id}")
    agent = get_agent()
    
    # Generate or use provided thread_id
    thread_id = request.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    logger.debug(f"Using thread_id: {thread_id}")
    
    async def generate():
        try:
            # Send thinking action immediately
            yield f"data: [ACTION]thinking[/ACTION]\n\n"
            
            # Use stream_mode="messages" for token-by-token streaming
            for msg, metadata in agent.stream(
                {"messages": [{"role": "user", "content": request.message}]},
                config=config,
                context=Context(user_id=request.user_id),
                stream_mode="messages"
            ):
                msg_type = getattr(msg, 'type', None)
                
                # Stream AI message content tokens
                if hasattr(msg, 'content') and msg.content:
                    if msg_type == 'AIMessageChunk' or msg_type == 'ai' or (hasattr(msg, 'role') and msg.role == 'assistant'):
                        # JSON-encode content to preserve newlines in SSE
                        encoded_content = json.dumps(msg.content)
                        yield f"data: [TEXT]{encoded_content}[/TEXT]\n\n"
            
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            yield f"data: [ERROR: {str(e)}]\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Thread-ID": thread_id
        }
    )
