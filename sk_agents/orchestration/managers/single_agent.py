"""
Single Agent Group Chat Manager

A group chat manager designed for single agent scenarios where we want the agent
to continue working until it has completed all its objectives and created
a final report.

This is extracted from the 5.1-code_exploration.ipynb notebook, preserving
the exact implementation to maintain compatibility with Semantic Kernel patterns.
"""

from typing import Dict
from typing_extensions import override

from semantic_kernel import Kernel
from semantic_kernel.agents.orchestration.group_chat import (
    BooleanResult,
    GroupChatManager,
    MessageResult,
    StringResult
)
from semantic_kernel.contents import ChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.connectors.ai.prompt_execution_settings import PromptExecutionSettings
from semantic_kernel.functions import KernelArguments
from semantic_kernel.prompt_template import KernelPromptTemplate, PromptTemplateConfig


class SingleAgentGroupChatManager(GroupChatManager):
    """Group chat manager for single agent that continues until objectives are complete.
    
    This manager is designed for a single agent scenario where we want the agent
    to continue working until it has completed all its objectives and created
    a final report.
    """

    topic: str
    service: ChatCompletionClientBase  # Type reference to the chat completion service
    
    termination_prompt: str = (
        "You are monitoring a code analysis agent working on the topic: '{{$topic}}'. "
        "Check if the agent has completed BOTH objectives:\n"
        "1. Comprehensive codebase analysis - The agent should have explored the directory structure, "
        "examined key files, and understood the system architecture.\n"
        "2. Testing all FileSystemPlugin functions - The agent should have tested all 5 functions: "
        "find_files, list_directory, read_file, search_in_files, and get_file_info.\n\n"
        "The agent should have provided a final markdown report with both sections:\n"
        "- Codebase Analysis Summary\n"
        "- FileSystemPlugin Tool Effectiveness Report\n\n"
        "Respond with True ONLY if both objectives are complete with the final markdown report. "
        "Otherwise, respond with False and explain what still needs to be done."
    )
    
    def __init__(self, topic: str, service, **kwargs) -> None:
        """Initialize the single agent group chat manager."""
        super().__init__(topic=topic, service=service, **kwargs)
        
    async def _render_prompt(self, prompt: str, arguments: KernelArguments) -> str:
        """Helper to render a prompt with arguments."""
        prompt_template_config = PromptTemplateConfig(template=prompt)
        prompt_template = KernelPromptTemplate(prompt_template_config=prompt_template_config)
        return await prompt_template.render(Kernel(), arguments=arguments)
    
    @override
    async def should_request_user_input(self, chat_history: ChatHistory) -> BooleanResult:
        """Single agent doesn't need user input."""
        return BooleanResult(
            result=False,
            reason="Single agent scenario does not require user input."
        )
    
    @override
    async def should_terminate(self, chat_history: ChatHistory) -> BooleanResult:
        """Check if the agent has completed both objectives."""
        # First check default termination conditions
        should_terminate = await super().should_terminate(chat_history)
        if should_terminate.result:
            return should_terminate
        
        # Create a copy of chat history for the termination check
        check_history = ChatHistory()
        check_history.messages = chat_history.messages.copy()
        
        # Add system prompt for termination check
        check_history.messages.insert(
            0,
            ChatMessageContent(
                role=AuthorRole.SYSTEM,
                content=await self._render_prompt(
                    self.termination_prompt,
                    KernelArguments(topic=self.topic)
                ),
            ),
        )
        
        # Add user prompt
        check_history.add_message(
            ChatMessageContent(
                role=AuthorRole.USER, 
                content="Check if the agent has completed both objectives and created the final report."
            ),
        )
        
        # Get LLM decision
        response = await self.service.get_chat_message_content(
            check_history,
            settings=PromptExecutionSettings(response_format=BooleanResult),
        )
        
        termination_result = BooleanResult.model_validate_json(response.content)
        
        print("\n" + "="*60)
        print(f"🤖 Termination Check - Should terminate: {termination_result.result}")
        print(f"📝 Reason: {termination_result.reason}")
        print("="*60 + "\n")
        
        return termination_result
    
    @override
    async def select_next_agent(
        self,
        chat_history: ChatHistory,
        participant_descriptions: dict[str, str],
    ) -> StringResult:
        """For single agent, always select the same agent."""
        # Get the single agent name
        agent_name = list(participant_descriptions.keys())[0]
        
        return StringResult(
            result=agent_name,
            reason="Single agent scenario - continuing with the only available agent."
        )
    
    @override
    async def filter_results(
        self,
        chat_history: ChatHistory,
    ) -> MessageResult:
        """Return the last message which should contain the final report."""
        if not chat_history.messages:
            raise RuntimeError("No messages in the chat history.")
        
        # Find the last assistant message (from our agent)
        for message in reversed(chat_history.messages):
            if message.role == AuthorRole.ASSISTANT:
                return MessageResult(
                    result=message,
                    reason="Returning the agent's final message containing the comprehensive report."
                )
        
        # Fallback to last message if no assistant message found
        return MessageResult(
            result=chat_history.messages[-1],
            reason="Returning the last message in the conversation."
        )