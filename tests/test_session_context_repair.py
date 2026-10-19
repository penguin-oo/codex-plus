import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import session_context_repair


class SessionContextRepairTests(unittest.TestCase):
    def test_auth_repair_removes_encrypted_reasoning_and_keeps_visible_history(self) -> None:
        session_id = "01a02c60-2b12-74e2-a53a-a61d6528b023"
        with tempfile.TemporaryDirectory() as temp_dir:
            session_file = Path(temp_dir) / f"rollout-{session_id}.jsonl"
            lines = [
                {
                    "type": "session_meta",
                    "payload": {"id": session_id},
                },
                {
                    "type": "response_item",
                    "payload": {
                        "type": "reasoning",
                        "id": "rs-cross-provider",
                        "summary": [],
                        "encrypted_content": "unreadable-by-official-account",
                    },
                },
                {
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": "keep this request"}],
                    },
                },
                {
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "assistant",
                        "phase": "final_answer",
                        "content": [{"type": "output_text", "text": "keep this answer"}],
                    },
                },
                {
                    "type": "event_msg",
                    "payload": {
                        "type": "item_completed",
                        "item": {
                            "type": "reasoning",
                            "id": "rs-cross-provider",
                            "encrypted_content": "unreadable-by-official-account",
                        },
                    },
                },
            ]
            session_file.write_text(
                "\n".join(json.dumps(item) for item in lines) + "\n",
                encoding="utf-8",
            )

            backup = session_context_repair.repair_session_for_codex_auth(
                session_id,
                session_file,
            )

            self.assertIsNotNone(backup)
            self.assertTrue(backup and backup.exists())
            repaired = [json.loads(line) for line in session_file.read_text(encoding="utf-8").splitlines()]
            self.assertEqual("session_meta", repaired[0]["type"])
            self.assertEqual("keep this request", repaired[1]["payload"]["content"][0]["text"])
            self.assertEqual("keep this answer", repaired[2]["payload"]["content"][0]["text"])
            self.assertNotIn("encrypted_content", repaired[3]["payload"]["item"])
            self.assertFalse(
                any(
                    item.get("payload", {}).get("type") == "reasoning"
                    for item in repaired
                    if isinstance(item, dict)
                )
            )

            self.assertIsNone(
                session_context_repair.repair_session_for_codex_auth(
                    session_id,
                    session_file,
                )
            )

    def test_stale_invalid_encrypted_error_is_removed_from_rollout_and_projection(self) -> None:
        session_id = "session-test"
        invalid_turn_id = "turn-invalid"
        invalid_item_id = "rs_invalid"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            session_file = root / f"rollout-{session_id}.jsonl"
            database_file = root / "thread_history.sqlite"
            invalid_message = (
                "invalid_encrypted_content: The encrypted content for item "
                f"{invalid_item_id} could not be verified."
            )
            lines = [
                {"ordinal": 0, "type": "session_meta", "payload": {"id": session_id}},
                {
                    "ordinal": 1,
                    "type": "response_item",
                    "payload": {
                        "type": "reasoning",
                        "id": "rs-valid",
                        "encrypted_content": "valid-official-content",
                    },
                },
                {
                    "ordinal": 2,
                    "type": "event_msg",
                    "payload": {
                        "type": "task_complete",
                        "turn_id": invalid_turn_id,
                        "last_agent_message": None,
                        "error": {"message": invalid_message},
                    },
                },
            ]
            session_file.write_text(
                "\n".join(json.dumps(item) for item in lines) + "\n",
                encoding="utf-8",
            )
            connection = sqlite3.connect(database_file)
            connection.executescript(
                """
                CREATE TABLE thread_items (
                    thread_id TEXT NOT NULL,
                    turn_id TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    item_json TEXT NOT NULL,
                    PRIMARY KEY (thread_id, turn_id, item_id)
                );
                CREATE TABLE thread_turns (
                    thread_id TEXT NOT NULL,
                    turn_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_json TEXT,
                    PRIMARY KEY (thread_id, turn_id)
                );
                CREATE TABLE thread_history_projection_state (
                    thread_id TEXT PRIMARY KEY,
                    next_rollout_byte_offset INTEGER NOT NULL,
                    next_rollout_ordinal INTEGER NOT NULL
                );
                """
            )
            connection.execute(
                "INSERT INTO thread_items VALUES (?, ?, ?, ?)",
                (session_id, invalid_turn_id, invalid_item_id, json.dumps({"type": "reasoning"})),
            )
            connection.execute(
                "INSERT INTO thread_items VALUES (?, ?, ?, ?)",
                (session_id, "turn-valid", "rs-valid", json.dumps({"type": "reasoning"})),
            )
            connection.execute(
                "INSERT INTO thread_turns VALUES (?, ?, ?, ?)",
                (session_id, invalid_turn_id, "failed", json.dumps({"message": invalid_message})),
            )
            connection.execute(
                "INSERT INTO thread_turns VALUES (?, ?, ?, ?)",
                (session_id, "turn-other", "failed", json.dumps({"message": "other error"})),
            )
            connection.execute(
                "INSERT INTO thread_history_projection_state VALUES (?, ?, ?)",
                (session_id, 999999, 999999),
            )
            connection.commit()
            connection.close()

            backup = session_context_repair.clear_invalid_encrypted_content_history(
                session_id,
                session_file,
                thread_history_db=database_file,
            )

            self.assertIsNotNone(backup)
            repaired = [json.loads(line) for line in session_file.read_text(encoding="utf-8").splitlines()]
            self.assertEqual("valid-official-content", repaired[1]["payload"]["encrypted_content"])
            self.assertIsNone(repaired[2]["payload"].get("error"))
            connection = sqlite3.connect(database_file)
            invalid_item_row = connection.execute(
                "SELECT 1 FROM thread_items WHERE thread_id=? AND item_id=?",
                (session_id, invalid_item_id),
            ).fetchone()
            valid_item_row = connection.execute(
                "SELECT 1 FROM thread_items WHERE thread_id=? AND item_id='rs-valid'",
                (session_id,),
            ).fetchone()
            repaired_turn = connection.execute(
                "SELECT status, error_json FROM thread_turns WHERE thread_id=? AND turn_id=?",
                (session_id, invalid_turn_id),
            ).fetchone()
            other_turn_status = connection.execute(
                "SELECT status FROM thread_turns WHERE thread_id=? AND turn_id='turn-other'",
                (session_id,),
            ).fetchone()[0]
            projection_cursor = connection.execute(
                "SELECT next_rollout_byte_offset, next_rollout_ordinal "
                "FROM thread_history_projection_state WHERE thread_id=?",
                (session_id,),
            ).fetchone()
            connection.close()
            self.assertIsNone(
                invalid_item_row
            )
            self.assertIsNotNone(valid_item_row)
            self.assertEqual(
                ("completed", None),
                repaired_turn,
            )
            self.assertEqual(
                "failed",
                other_turn_status,
            )
            self.assertEqual(
                (session_file.stat().st_size, 3),
                projection_cursor,
            )


if __name__ == "__main__":
    unittest.main()
