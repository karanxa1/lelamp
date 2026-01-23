"""Custom MIMO LLM with thinking disabled"""
from openai import AsyncOpenAI
from livekit.agents import llm, APIConnectOptions
from livekit.agents.llm import ChatContext, ChatChunk, ChoiceDelta, FunctionTool, RawFunctionTool
from typing import Any
import os
import uuid


class MimoLLM(llm.LLM):
    def __init__(
        self,
        model: str = "mimo-v2-flash",
        api_key: str | None = None,
        base_url: str = "https://api.xiaomimimo.com/v1",
        temperature: float = 0.3,
    ):
        super().__init__()
        self._model = model
        self._client = AsyncOpenAI(
            api_key=api_key or os.getenv("MIMO_API_KEY"),
            base_url=base_url,
            timeout=60.0,
        )
        self._temperature = temperature

    @property
    def model(self) -> str:
        return self._model

    def chat(
        self,
        *,
        chat_ctx: ChatContext,
        tools: list[FunctionTool | RawFunctionTool] | None = None,
        conn_options: APIConnectOptions = APIConnectOptions(),
        parallel_tool_calls: bool | None = None,
        tool_choice: llm.ToolChoice | None = None,
        extra_kwargs: dict[str, Any] | None = None,
    ) -> "MimoChatStream":
        return MimoChatStream(
            llm=self,
            chat_ctx=chat_ctx,
            tools=tools or [],
            conn_options=conn_options,
        )


class MimoChatStream(llm.LLMStream):
    def __init__(
        self,
        *,
        llm: MimoLLM,
        chat_ctx: ChatContext,
        tools: list[FunctionTool | RawFunctionTool],
        conn_options: APIConnectOptions,
    ):
        super().__init__(llm=llm, chat_ctx=chat_ctx, tools=tools, conn_options=conn_options)
        self._mimo_llm = llm

    async def _run(self) -> None:
        messages = []
        for msg in self._chat_ctx.items:
            if hasattr(msg, 'role') and hasattr(msg, 'content'):
                role = msg.role.value if hasattr(msg.role, 'value') else str(msg.role)
                content = ""
                if isinstance(msg.content, str):
                    content = msg.content
                elif isinstance(msg.content, list):
                    for part in msg.content:
                        if hasattr(part, 'text'):
                            content += part.text
                        elif isinstance(part, str):
                            content += part
                if content:
                    messages.append({"role": role, "content": content})

        response = await self._mimo_llm._client.chat.completions.create(
            model=self._mimo_llm._model,
            messages=messages,
            temperature=self._mimo_llm._temperature,
            stream=True,
            extra_body={"thinking": {"type": "disabled"}},
        )

        request_id = str(uuid.uuid4())
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                self._event_ch.send_nowait(
                    ChatChunk(
                        id=request_id,
                        delta=ChoiceDelta(
                            role="assistant",
                            content=chunk.choices[0].delta.content,
                        ),
                    )
                )
