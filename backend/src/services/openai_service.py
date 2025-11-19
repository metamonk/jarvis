"""OpenAI LLM service using Pipecat."""
from pipecat.services.openai.llm import OpenAILLMService as PipecatOpenAILLM
from pipecat.frames.frames import (
    Frame,
    LLMMessagesFrame,
    TextFrame,
    LLMFullResponseEndFrame
)
from pipecat.processors.aggregators.llm_response import (
    LLMAssistantResponseAggregator,
    LLMUserResponseAggregator
)
from loguru import logger
from typing import AsyncIterator, List, Dict, Any, Optional


class OpenAILLMService:
    """
    Wrapper for Pipecat's OpenAI LLM service.

    Provides conversational AI capabilities using GPT-4 Turbo.
    """

    def __init__(self, api_key: str):
        """
        Initialize OpenAI LLM service.

        Args:
            api_key: OpenAI API key
        """
        self.api_key = api_key
        self._service = None
        self._conversation_history: List[Dict[str, str]] = []
        logger.info("OpenAI LLM Service initialized")

    def create_service(
        self,
        model: str = "gpt-4-turbo-preview",
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs
    ) -> PipecatOpenAILLM:
        """
        Create a Pipecat OpenAI LLM service instance.

        Args:
            model: OpenAI model to use (default: gpt-4-turbo-preview)
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens in response
            **kwargs: Additional OpenAI parameters

        Returns:
            PipecatOpenAILLM: Configured OpenAI service
        """
        params = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }

        logger.info(f"Creating OpenAI LLM service with params: {params}")

        self._service = PipecatOpenAILLM(
            api_key=self.api_key,
            **params
        )

        return self._service

    def set_system_prompt(self, system_prompt: str):
        """
        Set the system prompt for the conversation.

        Args:
            system_prompt: System-level instructions for the AI
        """
        self._conversation_history = [
            {"role": "system", "content": system_prompt}
        ]
        logger.info(f"System prompt set: {system_prompt[:100]}...")

    def add_user_message(self, message: str):
        """
        Add a user message to conversation history.

        Args:
            message: User's message text
        """
        self._conversation_history.append({
            "role": "user",
            "content": message
        })
        logger.debug(f"User message added: {message}")

    def add_assistant_message(self, message: str):
        """
        Add an assistant message to conversation history.

        Args:
            message: Assistant's response text
        """
        self._conversation_history.append({
            "role": "assistant",
            "content": message
        })
        logger.debug(f"Assistant message added: {message}")

    async def process_messages(
        self,
        messages: Optional[List[Dict[str, str]]] = None
    ) -> AsyncIterator[Frame]:
        """
        Process messages and yield response frames.

        Args:
            messages: Optional message list (uses conversation history if None)

        Yields:
            Frame: LLM response frames
        """
        if not self._service:
            raise RuntimeError(
                "Service not created. Call create_service() first."
            )

        if messages is None:
            messages = self._conversation_history

        try:
            # Create LLM messages frame
            messages_frame = LLMMessagesFrame(messages=messages)

            # Process through OpenAI service with direction
            from pipecat.processors.frame_processor import FrameDirection
            async for frame in self._service.process_frame(
                messages_frame,
                FrameDirection.DOWNSTREAM
            ):
                yield frame

        except Exception as e:
            logger.error(f"Error processing messages: {e}")
            raise

    async def generate_response(self, user_message: str) -> str:
        """
        Generate a single response to a user message.

        Args:
            user_message: User's input text

        Returns:
            str: Assistant's response text
        """
        self.add_user_message(user_message)

        response_text = ""
        async for frame in self.process_messages():
            if isinstance(frame, TextFrame):
                response_text += frame.text
            elif isinstance(frame, LLMFullResponseEndFrame):
                # End of response
                break

        self.add_assistant_message(response_text)
        return response_text

    def clear_history(self, keep_system_prompt: bool = True):
        """
        Clear conversation history.

        Args:
            keep_system_prompt: If True, keep the system prompt
        """
        if keep_system_prompt and self._conversation_history:
            system_msg = next(
                (msg for msg in self._conversation_history
                 if msg["role"] == "system"),
                None
            )
            self._conversation_history = (
                [system_msg] if system_msg else []
            )
        else:
            self._conversation_history = []

        logger.info("Conversation history cleared")

    @property
    def is_ready(self) -> bool:
        """Check if service is ready to process messages."""
        return self._service is not None

    @property
    def history(self) -> List[Dict[str, str]]:
        """Get conversation history."""
        return self._conversation_history.copy()
