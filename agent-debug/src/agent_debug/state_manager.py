"""
A node is a function that can be executed.
A checkpoint is a record of the state of a node at a given execution attempt.
A state manager is a class that manages the state of the debugging session, including checkpoints and touched nodes.
A node can have multiple checkpoints, each representing a different execution attempt.
A node can be in one of the following modes:
- RUN: The node will be executed when called.
- CACHED: The node will apply the cached output when called.
"""
from enum import Enum
import threading
import json
import sys
import time
from typing import Dict, Any, List

class NodeStatus(Enum):
    RUN = "run"
    CACHED = "cached"

class Checkpoint:
    """A checkpoint is a record of the state of a node at a given execution attempt."""
    session_id: int
    inputs: Any
    output: Any
    execution_time: float
    timestamp: float
    status: NodeStatus
    error: str | None
    shared_store_state: Any
    
    def __init__(self, session_id: int, inputs: Any, output: Any, execution_time: float, timestamp: float|None=None,
     status: NodeStatus=NodeStatus.RUN, error: str|None=None, shared_store_state: Any|None=None):
        self.session_id = session_id
        self.inputs = inputs
        self.output = output
        self.execution_time = execution_time
        self.timestamp = timestamp or time.time()
        self.status = status or NodeStatus.RUN
        self.error = error or None
        self.shared_store_state = shared_store_state or None
class Node:
    """A node is a function that can be executed."""
    id: str
    checkpoints: List[Checkpoint]

    def __init__(self, id: str, checkpoints: List[Checkpoint]):
        self.id = id
        self.checkpoints = checkpoints

class StateManager:
    lock: threading.Lock
    nodes: Dict[str, Node]
    session_id: int
    shared_store: Any
    
    def to_json(self) -> str:
        nodes = json.dumps(self.nodes)
        return json.dumps({
            "session_id": self.session_id,
            "nodes": nodes,
        })

    def to_file(self, file_path: str):
        """Saves the state of the state manager to a file."""
        with open(file_path, "w") as f:
            json.dump(self.to_json(), f)

    def checkpoints_from_file(self, file_path: str):
        """Loads the state of the state manager from a file."""
        with open(file_path, "r") as f:
            data = json.load(f)
            self.nodes = {
                node["id"]: Node(
                    node["id"],
                    [Checkpoint(
                        checkpoint["session_id"],
                        checkpoint["inputs"],
                        checkpoint["output"],
                        checkpoint["execution_time"],
                        checkpoint["timestamp"],
                        checkpoint["status"],
                        checkpoint["error"])
                    for checkpoint in node["checkpoints"]]
                )
                for node in data["nodes"]
            }

    """Manages the state of the debugging session, including checkpoints and mode."""
    def __init__(self):
        self.lock = threading.Lock()
        self.nodes = {}
        self.session_id = int(time.time())

    def add_checkpoint(self, node_id: str, inputs: Any, output: Any, execution_time: float, shared_store_state: Any | None = None):
        """Records a checkpoint and prints it to stdout for the IDE."""
        with self.lock:
            checkpoint = Checkpoint(self.session_id, inputs, output, execution_time, shared_store_state=shared_store_state)
            if node_id not in self.nodes:
                self.nodes[node_id] = Node(node_id, [])
            self.nodes[node_id].checkpoints.append(checkpoint)


    def get_checkpoint(self, node_id: str) -> Checkpoint | None:
        """Retrieves the latest checkpoint for a given node."""
        with self.lock:
            if node_id in self.nodes and self.nodes[node_id].checkpoints:
                # Return the latest checkpoint for the node
                return self.nodes[node_id].checkpoints[-1]
            return None
    
    # def apply_checkpoint(self, checkpoint: Checkpoint):
    #     """Applies a checkpoint to the state manager - if it was cached."""
    #     with self.lock:
    #         if checkpoint.status == NodeStatus.CACHED:
    #             # TODO: this will not work since we dont have pointers, do something else
    #             self.shared_store = checkpoint.shared_store_state

# Singleton instance to be used by the decorators and runner
state_manager = StateManager()

