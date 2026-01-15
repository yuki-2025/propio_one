# WebSocket endpoint - Real-time Voice Chat (Simplified)
# Uses OpenAI Realtime API for voice-to-voice conversation

import asyncio
import json
import base64
import logging
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect

from app.services.realtime_service import RealtimeService
from app.config import settings

logger = logging.getLogger(__name__)


async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket 端点 - 简化版（纯语音聊天）

    流程：
    1. 接受前端连接
    2. 创建并连接 RealtimeService
    3. 启动两个并发任务：
       - handle_client: 前端 → OpenAI (音频)
       - handle_openai: OpenAI → 前端 (转录 + 音频)
    """
    await websocket.accept()
    logger.info("✅ Client connected")

    # 创建 RealtimeService
    service = RealtimeService(
        api_key=settings.openai_api_key,
        model=settings.openai_realtime_model,
        voice="alloy",
        instructions="""You are a helpful AI assistant. Be friendly, concise, and helpful.
Respond naturally in conversation. If the user asks a question, answer it directly.
If they want to chat, engage in friendly conversation."""
    )

    try:
        # 连接到 OpenAI
        logger.info("🔗 Connecting to OpenAI...")
        success = await service.connect()

        if not success:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Failed to connect to OpenAI Realtime API"
            }))
            await websocket.close()
            return

        logger.info("✅ Connected to OpenAI")

        # 启动两个并发任务
        await asyncio.gather(
            handle_client(websocket, service),
            handle_openai(websocket, service)
        )

    except WebSocketDisconnect:
        logger.info("🔌 Client disconnected")
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": str(e)
            }))
        except:
            pass
    finally:
        # 清理资源
        await service.disconnect()
        logger.info("🔌 Connection closed")


async def handle_client(websocket: WebSocket, service: RealtimeService):
    """
    处理前端消息 → OpenAI

    消息类型：
    - audio_chunk: 音频数据（base64）
    - audio_complete: 音频结束
    """
    audio_chunks_received = 0

    try:
        while True:
            data_raw = await websocket.receive_text()
            data = json.loads(data_raw)
            msg_type = data.get("type")

            if msg_type == "audio_chunk":
                # 发送音频到 OpenAI
                audio_b64 = data.get("data", "")
                audio_bytes = base64.b64decode(audio_b64)
                await service.send_audio(audio_bytes)
                audio_chunks_received += 1

            elif msg_type == "audio_complete":
                # 提交音频缓冲区（只有收到音频时才提交）
                if audio_chunks_received > 0:
                    await service.commit_audio()
                    logger.info(f"🎤 Audio committed ({audio_chunks_received} chunks)")
                    audio_chunks_received = 0
                else:
                    logger.warning("⚠️ audio_complete but no chunks, skipping")

    except WebSocketDisconnect:
        logger.info("🔌 Client disconnected (from handler)")
    except Exception as e:
        logger.error(f"❌ Error in handle_client: {e}")


async def handle_openai(websocket: WebSocket, service: RealtimeService):
    """
    处理 OpenAI 事件 → 前端

    直接转发所有事件到前端，不做任何业务逻辑处理。
    让 OpenAI Realtime API 的内置 LLM 处理对话。
    """
    try:
        async for event in service.listen_for_events():
            event_type = event.get("type")

            try:
                await websocket.send_text(json.dumps(event))
                if event_type not in ["audio_delta"]:  # 不记录频繁的音频事件
                    logger.info(f"📤 Forwarded: {event_type}")
            except Exception:
                # WebSocket 可能已关闭
                logger.debug("⚠️ Failed to send (connection closed)")
                break

    except WebSocketDisconnect:
        logger.info("🔌 Client disconnected (from OpenAI handler)")
    except Exception as e:
        logger.error(f"❌ Error in handle_openai: {e}")