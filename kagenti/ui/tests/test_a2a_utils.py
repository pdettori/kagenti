# Assisted by watsonx Code Assistant
# Copyright 2025 IBM Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import types


def make_log_container():
    class C:
        def markdown(self, *args, **kwargs):
            pass

        def warning(self, *args, **kwargs):
            pass

        def error(self, *args, **kwargs):
            pass

    return C()


def make_message_placeholder():
    class P:
        def markdown(self, *args, **kwargs):
            pass

        def error(self, *args, **kwargs):
            pass

    return P()


def make_chunk_root(event):
    # Simple wrapper object matching the structure used in the module
    class Resp:
        def __init__(self, result):
            self.result = result

    class Chunk:
        def __init__(self, root):
            self.root = root

        def model_dump_json(self, **kwargs):
            return "{}"

    return Chunk(Resp(event))


def test_task_final_message_returned(monkeypatch):
    import lib.a2a_utils as a2a_utils

    # Dummy classes to satisfy isinstance checks
    class DummyResp:
        pass

    class DummyTask:
        def __init__(self):
            self.id = "task-1"
            # Use dict-shaped parts to mirror wire format and avoid attribute issues
            self.status = types.SimpleNamespace(
                state="COMPLETED",
                message=types.SimpleNamespace(parts=[{"text": "Final result"}]),
            )

    # Monkeypatch the imported names inside the module so isinstance works
    monkeypatch.setattr(a2a_utils, "SendStreamingMessageSuccessResponse", DummyResp)
    monkeypatch.setattr(a2a_utils, "Task", DummyTask)

    # Create event and chunk
    event = DummyTask()
    chunk = make_chunk_root(event)

    # Ensure chunk.root is instance of DummyResp
    chunk.root.__class__ = DummyResp

    chunk_text, is_final = a2a_utils._process_a2a_stream_chunk(
        chunk, "test", make_log_container(), make_message_placeholder()
    )

    assert is_final is True
    assert "Final result" in chunk_text

    def test_artifact_formatting_and_mixed_parts(monkeypatch):
        """Ensure artifact data formatting is as expected and mixed text/data parts concatenate correctly."""
        import json
        import lib.a2a_utils as a2a_utils

        class DummyResp:
            pass

        class DummyArtifactEvent:
            def __init__(self):
                self.taskId = "task-format"
                # Mixed parts: text then data dict
                self.artifact = types.SimpleNamespace(
                    artifactId="fmt1",
                    parts=[
                        types.SimpleNamespace(text="Prefix text: "),
                        types.SimpleNamespace(
                            data={"name": "John Doe", "email": "john@example.com"}
                        ),
                    ],
                )

        monkeypatch.setattr(a2a_utils, "SendStreamingMessageSuccessResponse", DummyResp)
        monkeypatch.setattr(a2a_utils, "TaskArtifactUpdateEvent", DummyArtifactEvent)

        chunk = make_chunk_root(DummyArtifactEvent())
        chunk.root.__class__ = DummyResp
        txt, final = a2a_utils._process_a2a_stream_chunk(
            chunk, "fmt", make_log_container(), make_message_placeholder()
        )

        assert final is False
        # text prefix must be present
        assert "Prefix text:" in txt
        # data dict string must be present and contain keys in insertion order
        expected_data = {"name": "John Doe", "email": "john@example.com"}
        assert str(expected_data) in txt

    def test_wrapped_parts_extract_and_final_status(monkeypatch):
        """Wrapped parts (part.root.text) should be extracted; final status appends them to chat stream."""
        import lib.a2a_utils as a2a_utils

        class DummyResp:
            pass

        class DummyStatusUpdate:
            def __init__(self):
                self.taskId = "task-wrap"
                # status.message.parts contains wrapped part objects (part.root.text)
                self.status = types.SimpleNamespace(
                    state="completed",
                    message=types.SimpleNamespace(
                        parts=[
                            types.SimpleNamespace(
                                root=types.SimpleNamespace(text="Wrapped final text")
                            )
                        ]
                    ),
                )
                self.final = True

        monkeypatch.setattr(a2a_utils, "SendStreamingMessageSuccessResponse", DummyResp)
        monkeypatch.setattr(a2a_utils, "TaskStatusUpdateEvent", DummyStatusUpdate)

        chunk = make_chunk_root(DummyStatusUpdate())
        chunk.root.__class__ = DummyResp
        txt, final = a2a_utils._process_a2a_stream_chunk(
            chunk, "wrap", make_log_container(), make_message_placeholder()
        )
        assert final is True
        assert "Wrapped final text" in txt

    def test_jsonrpc_error_response_handling(monkeypatch):
        """JSONRPCErrorResponse chunks should return the formatted error message and be final."""
        import lib.a2a_utils as a2a_utils

        class DummyErrorResp:
            def __init__(self):
                self.error = types.SimpleNamespace(
                    code=321, message="boom", data="details"
                )

        monkeypatch.setattr(a2a_utils, "JSONRPCErrorResponse", DummyErrorResp)

        # Create a chunk whose root is a DummyErrorResp instance
        chunk = make_chunk_root(DummyErrorResp())
        chunk.root.__class__ = DummyErrorResp

        txt, final = a2a_utils._process_a2a_stream_chunk(
            chunk, "err", make_log_container(), make_message_placeholder()
        )
        assert final is True
        assert "A2A Error (Code: 321): boom" in txt


def test_task_intermediate_not_returned(monkeypatch):
    import lib.a2a_utils as a2a_utils

    class DummyResp:
        pass

    class DummyTask:
        def __init__(self):
            self.id = "task-2"
            self.status = types.SimpleNamespace(
                state="WORKING",
                message=types.SimpleNamespace(
                    parts=[{"text": "Task started, processing..."}]
                ),
            )

    monkeypatch.setattr(a2a_utils, "SendStreamingMessageSuccessResponse", DummyResp)
    monkeypatch.setattr(a2a_utils, "Task", DummyTask)

    event = DummyTask()
    chunk = make_chunk_root(event)
    chunk.root.__class__ = DummyResp

    chunk_text, is_final = a2a_utils._process_a2a_stream_chunk(
        chunk, "test", make_log_container(), make_message_placeholder()
    )

    assert is_final is False
    assert chunk_text == ""


def test_task_status_update_final_appended(monkeypatch):
    import lib.a2a_utils as a2a_utils

    class DummyResp:
        pass

    class DummyStatusUpdate:
        def __init__(self):
            self.taskId = "task-3"
            self.status = types.SimpleNamespace(
                state="completed",
                message=types.SimpleNamespace(
                    parts=[{"text": "Processed result: hello"}]
                ),
            )
            self.final = True

    monkeypatch.setattr(a2a_utils, "SendStreamingMessageSuccessResponse", DummyResp)
    monkeypatch.setattr(a2a_utils, "TaskStatusUpdateEvent", DummyStatusUpdate)

    event = DummyStatusUpdate()
    chunk = make_chunk_root(event)
    chunk.root.__class__ = DummyResp

    chunk_text, is_final = a2a_utils._process_a2a_stream_chunk(
        chunk, "test", make_log_container(), make_message_placeholder()
    )

    assert is_final is True
    assert "Processed result: hello" in chunk_text


import types

import pytest


def make_log_container():
    class C:
        def markdown(self, *args, **kwargs):
            pass

        def warning(self, *args, **kwargs):
            pass

        def error(self, *args, **kwargs):
            pass

    return C()


def make_message_placeholder():
    class P:
        def markdown(self, *args, **kwargs):
            pass

        def error(self, *args, **kwargs):
            pass

    return P()
    # Import from the ui package layout (tests run from the `ui/` directory)
    # import lib.a2a_utils as a2a_utils


def make_chunk_root(event):
    # Simple wrapper object matching the structure used in the module
    class Resp:
        def __init__(self, result):
            self.result = result

    class Chunk:
        def __init__(self, root):
            self.root = root

        def model_dump_json(self, **kwargs):
            return "{}"

    return Chunk(Resp(event))


def test_task_final_message_returned(monkeypatch):
    import lib.a2a_utils as a2a_utils

    # Dummy classes to satisfy isinstance checks
    class DummyResp:
        pass

    class DummyTask:
        def __init__(self):
            self.id = "task-1"
            self.status = types.SimpleNamespace(
                state="COMPLETED",
                message=types.SimpleNamespace(parts=[{"text": "Final result"}]),
            )

    # Monkeypatch the imported names inside the module so isinstance works
    monkeypatch.setattr(a2a_utils, "SendStreamingMessageSuccessResponse", DummyResp)
    monkeypatch.setattr(a2a_utils, "Task", DummyTask)

    # Create event and chunk
    event = DummyTask()
    chunk = make_chunk_root(event)

    # Ensure chunk.root is instance of DummyResp
    chunk.root.__class__ = DummyResp

    chunk_text, is_final = a2a_utils._process_a2a_stream_chunk(
        chunk, "test", make_log_container(), make_message_placeholder()
    )

    assert is_final is True
    assert "Final result" in chunk_text


def test_task_intermediate_not_returned(monkeypatch):
    import lib.a2a_utils as a2a_utils

    class DummyResp:
        pass

    class DummyTask:
        def __init__(self):
            self.id = "task-2"
            self.status = types.SimpleNamespace(
                state="WORKING",
                message=types.SimpleNamespace(
                    parts=[types.SimpleNamespace(text="Task started, processing...")]
                ),
            )

    monkeypatch.setattr(a2a_utils, "SendStreamingMessageSuccessResponse", DummyResp)
    monkeypatch.setattr(a2a_utils, "Task", DummyTask)

    event = DummyTask()
    chunk = make_chunk_root(event)
    chunk.root.__class__ = DummyResp

    chunk_text, is_final = a2a_utils._process_a2a_stream_chunk(
        chunk, "test", make_log_container(), make_message_placeholder()
    )

    assert is_final is False
    assert chunk_text == ""


def test_task_status_update_final_appended(monkeypatch):
    import lib.a2a_utils as a2a_utils

    class DummyResp:
        pass

    class DummyStatusUpdate:
        def __init__(self):
            self.taskId = "task-3"
            self.status = types.SimpleNamespace(
                state="completed",
                message=types.SimpleNamespace(
                    parts=[{"text": "Processed result: hello"}]
                ),
            )
            self.final = True

    monkeypatch.setattr(a2a_utils, "SendStreamingMessageSuccessResponse", DummyResp)
    monkeypatch.setattr(a2a_utils, "TaskStatusUpdateEvent", DummyStatusUpdate)

    event = DummyStatusUpdate()
    chunk = make_chunk_root(event)
    chunk.root.__class__ = DummyResp

    chunk_text, is_final = a2a_utils._process_a2a_stream_chunk(
        chunk, "test", make_log_container(), make_message_placeholder()
    )

    assert is_final is True
    assert "Processed result: hello" in chunk_text
