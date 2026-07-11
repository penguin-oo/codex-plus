import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import mobile_portal


def write_rollout(path: Path, events: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events),
        encoding="utf-8",
    )


class MobilePortalMessageTests(unittest.TestCase):
    def test_aborted_turn_keeps_latest_user_visible_assistant_progress(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            rollout = Path(temp_dir) / "rollout-session-1.jsonl"
            write_rollout(
                rollout,
                [
                    {
                        "timestamp": "2026-07-11T01:00:00Z",
                        "type": "response_item",
                        "payload": {
                            "type": "message",
                            "role": "user",
                            "content": [{"type": "input_text", "text": "question"}],
                        },
                    },
                    {
                        "timestamp": "2026-07-11T01:00:01Z",
                        "type": "event_msg",
                        "payload": {
                            "type": "agent_message",
                            "message": "first partial",
                            "phase": "commentary",
                        },
                    },
                    {
                        "timestamp": "2026-07-11T01:00:02Z",
                        "type": "event_msg",
                        "payload": {
                            "type": "agent_message",
                            "message": "latest partial",
                            "phase": "commentary",
                        },
                    },
                    {
                        "timestamp": "2026-07-11T01:00:03Z",
                        "type": "event_msg",
                        "payload": {"type": "turn_aborted", "reason": "interrupted"},
                    },
                ],
            )
            store = mobile_portal.CodexDataStore()
            with (
                mock.patch.object(store, "find_session_file", return_value=str(rollout)),
                mock.patch.object(mobile_portal, "HISTORY_FILE", Path(temp_dir) / "missing-history.jsonl"),
            ):
                messages = store.load_messages("session-1")

        assistant_messages = [item for item in messages if item["role"] == "assistant"]
        self.assertEqual(1, len(assistant_messages))
        self.assertEqual("latest partial", assistant_messages[0]["text"])
        self.assertGreater(int(assistant_messages[0]["ts"]), 0)

    def test_completed_turn_uses_final_answer_without_commentary_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            rollout = Path(temp_dir) / "rollout-session-1.jsonl"
            write_rollout(
                rollout,
                [
                    {
                        "timestamp": "2026-07-11T01:00:00Z",
                        "type": "response_item",
                        "payload": {
                            "type": "message",
                            "role": "user",
                            "content": [{"type": "input_text", "text": "question"}],
                        },
                    },
                    {
                        "timestamp": "2026-07-11T01:00:01Z",
                        "type": "event_msg",
                        "payload": {
                            "type": "agent_message",
                            "message": "commentary",
                            "phase": "commentary",
                        },
                    },
                    {
                        "timestamp": "2026-07-11T01:00:02Z",
                        "type": "response_item",
                        "payload": {
                            "type": "message",
                            "role": "assistant",
                            "phase": "final_answer",
                            "content": [{"type": "output_text", "text": "final answer"}],
                        },
                    },
                    {
                        "timestamp": "2026-07-11T01:00:03Z",
                        "type": "event_msg",
                        "payload": {
                            "type": "task_complete",
                            "last_agent_message": "final answer",
                        },
                    },
                ],
            )
            store = mobile_portal.CodexDataStore()
            with (
                mock.patch.object(store, "find_session_file", return_value=str(rollout)),
                mock.patch.object(mobile_portal, "HISTORY_FILE", Path(temp_dir) / "missing-history.jsonl"),
            ):
                messages = store.load_messages("session-1")

        assistant_texts = [item["text"] for item in messages if item["role"] == "assistant"]
        self.assertEqual(["final answer"], assistant_texts)


if __name__ == "__main__":
    unittest.main()
