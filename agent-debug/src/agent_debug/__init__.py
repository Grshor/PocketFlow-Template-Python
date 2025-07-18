"""
agent-debug package.

This package provides a time-travel debugger engine for Python applications,
particularly useful for agent-based systems.
"""
from .decorators import recordable_node
from .state_manager import state_manager

# Make the primary decorator and the state manager instance easily importable
__all__ = ['recordable_node', 'state_manager'] 


# TODO: https://www.perplexity.ai/search/konechno-davaite-detalno-razbe-bO4azev4TwmmvMfADdIGXQ#2
# TODO: https://www.perplexity.ai/search/konechno-davaite-detalno-razbe-bO4azev4TwmmvMfADdIGXQ#1
# TODO: добыча данных по вызову из LLM