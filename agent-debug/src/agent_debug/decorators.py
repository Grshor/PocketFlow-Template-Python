import functools
import time
import json
from .state_manager import state_manager, Checkpoint

def find_shared(args):
    """
    Finds a dictionary in the arguments, which is assumed to be the shared state.
    """
    for arg in args:
        if isinstance(arg, dict):
            return arg
    return None

def recordable_node(func):
    """
    A decorator that records the inputs and outputs of a function,
    allowing for time-travel debugging by replaying from a checkpoint.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Use the function's fully qualified name as a unique ID
        node_id = func.__qualname__

        # if a cached checkpoint exists, use it.
        cached_checkpoint = state_manager.get_checkpoint(node_id)
        if cached_checkpoint and cached_checkpoint.shared_store_state:
            shared = find_shared(args)
            if shared is not None:
                shared.clear()
                shared.update(cached_checkpoint.shared_store_state)
            return cached_checkpoint.output
        
        # If no cache exists, execute the function normally.
        start_time = time.thread_time()
        output = func(*args, **kwargs)
        end_time = time.thread_time()
        
        execution_time = end_time - start_time
        
        # Simple serialization for inputs. A robust solution would use a library
        # like pickle or a custom serializer.
        try:
            inputs = {"args": args, "kwargs": kwargs}
            json.dumps(inputs) # Test serializability
        except (TypeError, OverflowError):
            inputs = {"args": str(args), "kwargs": str(kwargs), "unserializable": True}

        shared = find_shared(args)
        state_manager.add_checkpoint(node_id, inputs, output, execution_time, shared_store_state=shared)
        
        return output

    return wrapper