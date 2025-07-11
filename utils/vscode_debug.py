import functools
import debugpy

def vscode_breakpoint(func):
    """Decorator to trigger a VSCode debug breakpoint before function execution."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        debugpy.breakpoint()
        result = func(*args, **kwargs)
        debugpy.breakpoint()

        return result
    return wrapper 

