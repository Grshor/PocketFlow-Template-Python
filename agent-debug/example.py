# This is an example script to demonstrate the agent-debug library.
# To run it with the debugger:
# python -m agent_debug.runner example.py

try:
    # This will work if 'agent-debug' is installed as a package
    from agent_debug.decorators import recordable_node
except ImportError:
    # This is a fallback for running directly from the source tree
    from src.agent_debug.decorators import recordable_node

import time
import random

@recordable_node
def get_user_data(user_id: int) -> dict:
    """Simulates fetching user data from a database or API."""
    print(f"EXECUTING: get_user_data for user: {user_id}")
    time.sleep(1) # Simulate I/O latency
    return {"id": user_id, "name": "Jane Doe", "email": "jane.doe@example.com"}

@recordable_node
def process_data(data: dict) -> dict:
    """Simulates a data processing step that might fail."""
    print(f"EXECUTING: process_data with: {data}")
    time.sleep(1)
    
    # Introduce a chance of a simulated error
    if random.random() < 0.5:
        data["status"] = "processed_with_error"
        print("  -> Simulated an error during processing.")
    else:
        data["status"] = "processed_successfully"
        print("  -> Data processed successfully.")
        
    return data

@recordable_node
def finalize_processing(processed_data: dict) -> dict:
    """Simulates a final step, like saving to a database."""
    print(f"EXECUTING: finalize_processing with: {processed_data}")
    time.sleep(0.5)
    return {"final_status": processed_data["status"], "message": "Workflow complete."}

def main():
    """The main execution flow of the script."""
    print("\n--- Starting example script flow ---")
    user_data = get_user_data(user_id=42)
    processed_data = process_data(user_data)
    final_result = finalize_processing(processed_data)
    print("--- Example script finished ---")
    print(f"\nFinal result: {final_result}\n")

if __name__ == "__main__":
    main() 