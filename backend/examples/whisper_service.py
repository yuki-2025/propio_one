"""
Whisper 语音转文字服务
使用 OpenAI Whisper API 将音频转换为文本
"""

import os
import logging
from typing import Optional
from openai import OpenAI
from fastapi import UploadFile

# 配置日志
logger = logging.getLogger(__name__)


class WhisperService:
    """
    Whisper 语音识别服务
    封装 OpenAI Whisper API 调用
    """

    def __init__(self):
        """初始化 OpenAI 客户端"""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("未找到 OPENAI_API_KEY 环境变量")

        self.client = OpenAI(api_key=api_key)
        logger.info("WhisperService 初始化完成")

    async def transcribe_audio(self, audio_file: UploadFile) -> str:
        """
        将音频文件转换为文本

        Args:
            audio_file: FastAPI 上传的音频文件

        Returns:
            str: 识别的文本内容（空文件返回空字符串）

        Raises:
            Exception: 如果 API 调用失败
        """
        try:
            logger.info(f"开始转录音频: {audio_file.filename}")

            # 读取音频文件内容
            audio_content = await audio_file.read()

            # 检查是否为空文件（用于触发初始 greeting）
            if len(audio_content) == 0:
                logger.info("检测到空音频文件，返回空字符串（触发 greeting）")
                return ""

            # 重置文件指针（以防后续需要再次读取）
            await audio_file.seek(0)

            # 调用 Whisper API
            # 注意：Whisper API 需要文件对象，我们需要创建一个临时的文件对象
            from io import BytesIO
            audio_buffer = BytesIO(audio_content)
            audio_buffer.name = audio_file.filename or "audio.webm"

            logger.info("正在调用 Whisper API...")

            # 调用 OpenAI Whisper API
            # 不指定 language 参数，让 Whisper 自动检测语言（支持中文、英文等多种语言）
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_buffer
            )

            # 提取文本
            text = transcript.text.strip()

            logger.info(f"转录完成，识别文本: {text}")

            return text

        except Exception as e:
            logger.error(f"Whisper API 调用失败: {str(e)}")
            # 如果是格式错误且文件很小，可能是初始触发，返回空字符串
            if "Invalid file format" in str(e) or "400" in str(e):
                logger.info("检测到无效格式但文件很小，返回空字符串（触发 greeting）")
                return ""
            raise Exception(f"语音识别失败: {str(e)}")


# 创建全局单例实例
_whisper_service: Optional[WhisperService] = None


def get_whisper_service() -> WhisperService:
    """
    获取 WhisperService 单例实例

    Returns:
        WhisperService: Whisper 服务实例
    """
    global _whisper_service
    if _whisper_service is None:
        _whisper_service = WhisperService()
    return _whisper_service