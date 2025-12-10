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
from conftest import make_log_container, make_message_placeholder, make_chunk_root


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


def test_task_artifact_image_rendering(monkeypatch):
    import lib.a2a_utils as a2a_utils

    class DummyResp:
        pass

    class DummyArtifactUpdate:
        def __init__(self):
            self.taskId = "task-4"
            self.artifact = types.SimpleNamespace(
                artifactId="b9212720-7a02-40da-b245-3c46a19cdc91",
                name="image.jpeg",
                parts=[
                    types.SimpleNamespace(
                        kind="data",
                        data={
                            "content": "/9j/4Q==",
                            "content_encoding": "base64",
                            "content_type": "image/jpeg",
                        },
                    )
                ],
            )

    monkeypatch.setattr(a2a_utils, "SendStreamingMessageSuccessResponse", DummyResp)
    monkeypatch.setattr(a2a_utils, "TaskArtifactUpdateEvent", DummyArtifactUpdate)

    event = DummyArtifactUpdate()
    chunk = make_chunk_root(event)
    chunk.root.__class__ = DummyResp

    chunk_text, is_final = a2a_utils._process_a2a_stream_chunk(
        chunk, "test", make_log_container(), make_message_placeholder()
    )

    # Artifact updates are not final events
    assert is_final is False
    # Check for img tag and base64 content
    assert '<img src="data:image/jpeg;base64,/9j/4Q' in chunk_text
    assert 'alt="image.jpeg"' in chunk_text
