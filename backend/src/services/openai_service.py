"""OpenAI LLM service using Pipecat."""
from pipecat.services.openai.llm import OpenAILLMService as PipecatOpenAILLM
from pipecat.frames.frames import (
    Frame,
    LLMMessagesFrame,
    TextFrame,
    LLMFullResponseEndFrame,
    StartFrame,
    LLMTextFrame
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
        self._client = None  # Initialize as None, will be created on first use

        # Validate API key format
        if not api_key or not api_key.startswith(('sk-', 'sk-proj-')):
            logger.warning(f"⚠️ OpenAI API key may be invalid. Key prefix: {api_key[:10] if api_key else 'None'}")

        logger.info(f"OpenAI LLM Service initialized with API key: {api_key[:20]}...")

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

        # Store parameters for direct API calls
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

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
            from pipecat.processors.frame_processor import FrameDirection

            # NOTE: This method is designed to work within a Pipecat pipeline context.
            # In production, this will be called within a PipelineTask with proper
            # TaskManager initialization.

            # Create LLM messages frame
            messages_frame = LLMMessagesFrame(messages=messages)

            # Process through OpenAI service
            result_frames = await self._service.process_frame(
                messages_frame,
                FrameDirection.DOWNSTREAM
            )

            # Yield frames from the result
            if result_frames:
                for frame in result_frames:
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
        logger.info(f"🔵 generate_response called with: {user_message}")
        self.add_user_message(user_message)

        # Use direct OpenAI API call instead of Pipecat frames
        try:
            logger.info("📞 Attempting to import OpenAI...")
            import openai
            logger.info("✅ OpenAI imported successfully")

            # Initialize OpenAI client if not already done
            if self._client is None:
                logger.info(f"🔑 Initializing OpenAI client with API key: {self.api_key[:10]}...")
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=self.api_key)
                logger.info("✅ OpenAI client initialized")

            logger.info(f"📤 Sending request to OpenAI API with {len(self._conversation_history)} messages...")
            logger.debug(f"Model: {self._model or 'gpt-4-turbo-preview'}")
            logger.debug(f"Temperature: {self._temperature or 0.7}")
            logger.debug(f"Max tokens: {self._max_tokens or 1024}")

            # Generate response using direct API
            response = await self._client.chat.completions.create(
                model=self._model or "gpt-4-turbo-preview",
                messages=self._conversation_history,
                temperature=self._temperature or 0.7,
                max_tokens=self._max_tokens or 1024,
                stream=False
            )
            logger.info("✅ Received response from OpenAI API")

            response_text = response.choices[0].message.content
            logger.info(f"📝 Response text: {response_text[:100]}...")
            self.add_assistant_message(response_text)
            return response_text

        except Exception as e:
            logger.error(f"❌ Error generating response: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error details: {str(e)}")
            import traceback
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            # Fallback to Pipecat method if direct API fails
            response_text = ""
            async for frame in self.process_messages():
                # Handle both TextFrame and LLMTextFrame
                if isinstance(frame, (TextFrame, LLMTextFrame)):
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
