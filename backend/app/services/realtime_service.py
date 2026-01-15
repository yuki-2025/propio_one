# OpenAI Realtime API 服务（简化版 - 只做音频 I/O）
# Simplified version - Audio I/O only (STT + TTS)

import json
import base64
import logging
from typing import Optional, AsyncGenerator, Dict, Any
import websockets
import asyncio

logger = logging.getLogger(__name__)


class RealtimeService:
    """
    OpenAI Realtime API 客户端（简化版）

    功能：
    1. 连接 OpenAI Realtime API
    2. 处理音频输入（用户语音 → 文本 STT）
    3. 处理音频输出（文本 → 语音 TTS）
    4. 业务逻辑由外部 State Machine 控制
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-realtime",
        voice: str = "marin",
        instructions: Optional[str] = None
    ):
        """
        初始化 RealtimeService

        参数:
            api_key: OpenAI API Key
            model: Realtime API 模型名称
            voice: 语音类型（alloy, echo, shimmer, marin 等）
            instructions: 自定义系统指令（默认为简单的 TTS 指令）
        """
        self.api_key = api_key
        self.model = model
        self.voice = voice
        self.instructions = instructions or "You are a text-to-speech system. When you receive a message, repeat it exactly word for word. Do not add any extra content or change anything."

        # OpenAI WebSocket
        self.ws_url = f"wss://api.openai.com/v1/realtime?model={model}"
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False

    async def connect(self) -> bool:
        """
        连接到 OpenAI Realtime API

        步骤：
        1. 建立 OpenAI WebSocket 连接
        2. 配置 session（音频配置 + VAD）
        """
        try:
            # 连接 OpenAI Realtime API
            logger.info(f"🔗 Connecting to OpenAI: {self.ws_url}")
            self.ws = await websockets.connect(
                self.ws_url,
                additional_headers={"Authorization": f"Bearer {self.api_key}"}
            )

            # 配置会话（使用 GA 最新完整语法）
            session_config = {
                "type": "session.update",        # 事件类型，固定 "session.update"
                "session": {
                    # 必填字段
                    "type": "realtime",          # 会话类型，Realtime 一律 "realtime"
                    "model": self.model,         # 使用的 Realtime 模型名（gpt-realtime 等）

                    # 音频配置（完整的 GA 结构）
                    "audio": {
                        "input": {
                            "format": {
                                "type": "audio/pcm",   # 输入音频格式
                                "rate": 24000          # PCM 采样率（固定 24000）
                            },
                            # 可选：输入音频转写（用于记录/调试）
                            "transcription": {
                                "language": "en",              # 输入语言 ISO-639-1
                                "model": "gpt-4o-transcribe"   # 转写模型
                            },
                            # VAD 语音活动检测（完整参数）
                            "turn_detection": {
                                "type": "server_vad",          # 服务器端 VAD
                                "create_response": True,       # 检测到说完后自动触发回复 ← 改为 True
                                #"idle_timeout_ms": 15000,      # 长时间沉默后强制让模型说话
                                "interrupt_response": True,    # 新一轮说话打断当前回复
                                "prefix_padding_ms": 500,      # VAD 截取前面保留的毫秒
                                "silence_duration_ms": 800,    # 判定"说完"的静音长度（缩短响应速度）
                                "threshold": 0.5               # 触发阈值 (0~1)，降低以提高灵敏度
                            },
                            "noise_reduction": {       # 输入降噪；null 表示关闭
                                "type": "near_field",  # "near_field"：耳机/近讲；"far_field"：笔记本/会议室麦
                            },
                        },
                        "output": {
                            "format": {
                                "type": "audio/pcm",   # 输出音频格式
                                "rate": 24000          # 输出采样率（必填）
                            },
                            "speed": 1,              # 语速：0.25~1.5，默认 1.0
                            "voice": self.voice        # 语音类型（alloy/echo/shimmer/marin 等）
                        },
                    },

                    # 输出模态（音频+文本）
                    "output_modalities": ["audio"],  # 需要文本转录用于调试

                    # 系统指令（只做 TTS，不做业务逻辑）
                    "instructions": self.instructions
                }
            }

            await self.ws.send(json.dumps(session_config))
            logger.info("✅ Session configured (audio I/O only)")

            self.is_connected = True
            logger.info("✅ Connected to OpenAI Realtime API")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to connect: {e}")
            self.is_connected = False
            return False

    async def send_audio(self, audio_bytes: bytes):
        """发送音频数据"""
        if not self.ws:
            raise RuntimeError("Not connected")

        audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
        await self.ws.send(json.dumps({
            "type": "input_audio_buffer.append",
            "audio": audio_b64
        }))

    async def commit_audio(self):
        """提交音频缓冲区"""
        if not self.ws:
            raise RuntimeError("Not connected")

        await self.ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
        logger.info("🎤 Audio committed")

    async def listen_for_events(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        监听 OpenAI 事件（只处理音频和转录事件）

        事件类型：
        - session.created: 会话创建
        - conversation.item.input_audio_transcription.completed: 用户语音转录完成
        - response.output_audio_transcript.delta: AI 回复文本增量
        - response.output_audio.delta: AI 音频增量
        - error: 错误事件
        """
        if not self.ws:
            raise RuntimeError("Not connected")

        try:
            async for message in self.ws:
                event = json.loads(message)
                event_type = event.get("type")

                logger.debug(f"📥 OpenAI event: {event_type}")

                # ===== 基础事件 =====

                if event_type == "session.created":
                    yield {"type": "connection_established", "message": "Connected to AI agent"}

                elif event_type == "session.updated":
                    logger.info("✅ Session updated successfully")

                elif event_type == "conversation.item.input_audio_transcription.completed":
                    transcript = event.get("transcript", "")
                    yield {"type": "user_transcript", "text": transcript}
                    logger.info(f"🎤 User said: {transcript}")

                # ===== 音频和文本输出事件 =====

                elif event_type == "response.output_audio_transcript.delta":
                    # AI 回复的文本转录（增量）
                    delta = event.get("delta", "")
                    yield {"type": "agent_transcript_delta", "text": delta}

                elif event_type == "response.output_audio_transcript.done":
                    # AI 回复的文本转录（完成）
                    transcript = event.get("transcript", "")
                    yield {"type": "agent_transcript_complete", "text": transcript}
                    logger.info(f"🤖 Agent said: {transcript}")

                elif event_type == "response.output_audio.delta":
                    # AI 回复的音频数据（增量）
                    audio_delta = event.get("delta", "")
                    if audio_delta:
                        logger.info(f"🔊 Audio delta received: {len(audio_delta)} chars")
                        yield {"type": "audio_delta", "audio": audio_delta}
                    else:
                        logger.warning("⚠️ Audio delta event but no data")

                elif event_type == "response.output_audio.done":
                    # AI 回复的音频数据（完成）
                    await asyncio.sleep(0.5)
                    yield {"type": "audio_complete"} 

                elif event_type == "response.done":
                    yield {"type": "response_complete"}
                
                # [新增] 监听打断事件，确认是否是 VAD 误触导致最后一句没念完
                elif event_type == "conversation.item.truncated":
                    logger.warning("⚠️ AI speech truncated by user interruption (VAD triggered)")
                    yield {"type": "interruption", "message": "User interrupted AI"}
                
                # [新增] 核心调试：监听 VAD 说话开始事件
                # 如果看到这条日志，说明麦克风听到了声音，导致 AI 闭嘴
                elif event_type == "input_audio_buffer.speech_started":
                    logger.warning("🔇 VAD detected speech start (Background noise/Echo?) - AI audio stopped")
                    yield {"type": "speech_started"}

                # ===== 错误处理 =====

                elif event_type == "error":
                    error_msg = event.get("error", {}).get("message", "Unknown error")
                    logger.error(f"❌ OpenAI error: {error_msg}")
                    yield {"type": "error", "message": error_msg}

                # ===== 未知事件（用于调试）=====
                else:
                    # 记录所有未处理的事件类型（帮助发现 GA 新增的事件）
                    if event_type and not event_type.startswith("input_audio_buffer"):
                        logger.debug(f"🔍 Unhandled event: {event_type}")

        except Exception as e:
            logger.error(f"❌ Error listening for events: {e}")
            yield {"type": "error", "message": str(e)}

    async def create_conversation_item(self, text: str, role: str = "assistant"):
        """
        手动创建对话项（用于 state machine 控制对话）

        注意：为了触发 TTS，我们创建 user message 而不是 assistant message，
        然后让 Realtime API 根据 instructions 复述这条消息

        Args:
            text: 要说的文本内容
            role: 角色（这里会被强制改为 "user"）
        """
        if not self.ws:
            raise RuntimeError("Not connected")

        # 始终创建 user message，让 Realtime API 复述
        await self.ws.send(json.dumps({
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "system",  # 强制使用 user role
                "content": [
                    {
                        "type": "input_text",
                        "text": text
                    }
                ]
            }
        }))
        logger.info(f"📝 Created user message for TTS: {text[:50]}...")

    async def trigger_response(self):
        """
        触发 Realtime API 生成回复（TTS）

        这会让 OpenAI 将刚创建的 assistant 消息转换为语音并发送
        """
        if not self.ws:
            raise RuntimeError("Not connected")

        await self.ws.send(json.dumps({
            "type": "response.create"
        }))
        logger.info("🎤 Triggered response generation")

    async def disconnect(self):
        """
        断开连接
        """
        # 断开 OpenAI
        if self.ws:
            await self.ws.close()
            self.ws = None

        self.is_connected = False
        logger.info("🔌 Disconnected from OpenAI")