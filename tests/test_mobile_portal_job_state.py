import unittest
import json
from unittest import mock

import mobile_portal


class FakeDataStore:
    def __init__(self, partial_message: str = "") -> None:
        self.partial_message = partial_message

    def latest_task_complete_message(self, session_id: str, since_ts: int = 0) -> tuple[int, str]:
        return 0, ""

    def latest_partial_assistant_message(self, session_id: str, since_ts: int = 0) -> tuple[int, str]:
        return mobile_portal.now_ts(), self.partial_message


class MobileJobStateTests(unittest.TestCase):
    def make_running_job(self) -> tuple[mobile_portal.JobRunner, str, str]:
        runner = mobile_portal.JobRunner(FakeDataStore())
        session_id = "session-1"
        job_id = "job-1"
        runner.jobs[job_id] = {
            "job_id": job_id,
            "status": "running",
            "session_id": session_id,
            "created_at": mobile_portal.now_ts(),
            "heartbeat_at": mobile_portal.now_ts(),
            "pid": 0,
            "live_text": "partial reply",
            "last_message": "partial reply",
            "error": "",
        }
        runner.active_sessions.add(session_id)
        return runner, session_id, job_id

    def test_dead_stale_job_is_retained_as_failed(self) -> None:
        runner = mobile_portal.JobRunner(FakeDataStore())
        session_id = "session-1"
        job_id = "job-1"
        stale_at = mobile_portal.now_ts() - mobile_portal.RUNNING_JOB_GRACE_SECONDS - 1
        runner.jobs[job_id] = {
            "job_id": job_id,
            "status": "running",
            "session_id": session_id,
            "created_at": stale_at,
            "heartbeat_at": stale_at,
            "pid": 999999,
            "live_text": "partial reply",
            "last_message": "partial reply",
            "error": "",
        }
        runner.active_sessions.add(session_id)

        with (
            mock.patch.object(runner, "_is_pid_running", return_value=False),
            mock.patch.object(mobile_portal, "list_windows_process_rows", return_value=[]),
        ):
            runner._recover_stale_session_locked(session_id)

        self.assertIn(job_id, runner.jobs)
        job = runner.jobs[job_id]
        self.assertEqual("failed", job["status"])
        self.assertEqual("partial reply", job["live_text"])
        self.assertEqual("partial reply", job["last_message"])
        self.assertEqual(0, job["pid"])
        self.assertGreater(int(job["finished_at"]), 0)
        self.assertEqual(
            "Reply interrupted. The response may be incomplete.",
            job["error"],
        )
        self.assertNotIn(session_id, runner.active_sessions)

    def test_error_event_records_diagnostic_without_finishing_job(self) -> None:
        runner, session_id, job_id = self.make_running_job()

        detected_session_id, completion_seen = runner._handle_codex_event(
            job_id,
            {"type": "error", "message": "insufficient quota"},
            session_id,
        )

        job = runner.jobs[job_id]
        self.assertEqual(session_id, detected_session_id)
        self.assertFalse(completion_seen)
        self.assertEqual("running", job["status"])
        self.assertEqual("", job["error"])
        self.assertEqual("insufficient quota", job["diagnostic_error"])

    def test_non_object_json_event_is_ignored(self) -> None:
        runner, session_id, job_id = self.make_running_job()

        detected_session_id, completion_seen = runner._handle_codex_event(
            job_id,
            "standalone quoted tool output",
            session_id,
        )

        self.assertEqual(session_id, detected_session_id)
        self.assertFalse(completion_seen)
        self.assertEqual("running", runner.jobs[job_id]["status"])

    def test_event_handler_failure_terminates_codex_process_tree(self) -> None:
        runner, session_id, job_id = self.make_running_job()
        process = mock.Mock()
        process.pid = 4242
        process.stdout = iter([json.dumps({"type": "thread.started", "thread_id": session_id}) + "\n"])

        with (
            mock.patch.object(mobile_portal.subprocess, "Popen", return_value=process),
            mock.patch.object(runner, "_handle_codex_event", side_effect=RuntimeError("bad event")),
            mock.patch.object(runner, "_terminate_pid", return_value=True) as terminate_pid,
        ):
            with self.assertRaisesRegex(RuntimeError, "bad event"):
                runner._run_codex_process(job_id, ["codex"], ".", session_id)

        terminate_pid.assert_called_once_with(4242)

    def test_agent_message_event_updates_live_partial_reply(self) -> None:
        runner, session_id, job_id = self.make_running_job()
        runner.jobs[job_id]["live_text"] = ""
        runner.jobs[job_id]["last_message"] = ""

        detected_session_id, completion_seen = runner._handle_codex_event(
            job_id,
            {
                "type": "event_msg",
                "payload": {
                    "type": "agent_message",
                    "message": "partial reply from commentary",
                    "phase": "commentary",
                },
            },
            session_id,
        )

        job = runner.jobs[job_id]
        self.assertEqual(session_id, detected_session_id)
        self.assertFalse(completion_seen)
        self.assertEqual("partial reply from commentary", job["live_text"])
        self.assertEqual("partial reply from commentary", job["last_message"])

    def test_turn_completed_promotes_latest_item_agent_message_to_final_answer(self) -> None:
        runner, session_id, job_id = self.make_running_job()
        runner.jobs[job_id]["live_text"] = ""
        runner.jobs[job_id]["last_message"] = ""

        _detected_session_id, message_completion_seen = runner._handle_codex_event(
            job_id,
            {
                "type": "item.completed",
                "item": {
                    "type": "agent_message",
                    "text": "final answer from codex exec",
                },
            },
            session_id,
        )
        detected_session_id, turn_completion_seen = runner._handle_codex_event(
            job_id,
            {"type": "turn.completed", "usage": {}},
            session_id,
        )

        job = runner.jobs[job_id]
        self.assertEqual(session_id, detected_session_id)
        self.assertFalse(message_completion_seen)
        self.assertTrue(turn_completion_seen)
        self.assertTrue(job["has_final_answer"])
        self.assertEqual("final answer from codex exec", job["last_message"])

    def test_cancel_job_recovers_partial_reply_from_rollout(self) -> None:
        runner = mobile_portal.JobRunner(FakeDataStore("rollout partial reply"))
        session_id = "session-1"
        job_id = "job-1"
        runner.jobs[job_id] = {
            "job_id": job_id,
            "status": "running",
            "session_id": session_id,
            "created_at": mobile_portal.now_ts(),
            "heartbeat_at": mobile_portal.now_ts(),
            "pid": 123,
            "live_text": "",
            "last_message": "",
            "error": "",
        }
        runner.active_sessions.add(session_id)

        with mock.patch.object(runner, "_terminate_pid"):
            result = runner.cancel_job(job_id)

        self.assertEqual("cancelled", result["status"])
        self.assertEqual("rollout partial reply", result["live_text"])
        self.assertEqual("rollout partial reply", result["last_message"])

    def test_quota_telemetry_at_100_percent_does_not_finish_job(self) -> None:
        runner, session_id, job_id = self.make_running_job()

        runner._handle_codex_event(
            job_id,
            {
                "type": "event_msg",
                "payload": {
                    "type": "token_count",
                    "rate_limits": {"primary": {"used_percent": 100.0}},
                },
            },
            session_id,
        )

        job = runner.jobs[job_id]
        self.assertEqual("running", job["status"])
        self.assertEqual("", job["error"])
        self.assertNotIn("diagnostic_error", job)

    def test_failed_finish_exposes_generic_error_and_keeps_diagnostic(self) -> None:
        runner, session_id, job_id = self.make_running_job()

        runner._finish_job(
            job_id,
            "failed",
            session_id,
            "",
            "provider returned insufficient quota",
            release_session=session_id,
        )

        job = runner.jobs[job_id]
        self.assertEqual("failed", job["status"])
        self.assertEqual("partial reply", job["live_text"])
        self.assertEqual("partial reply", job["last_message"])
        self.assertEqual(
            "Reply interrupted. The response may be incomplete.",
            job["error"],
        )
        self.assertEqual("provider returned insufficient quota", job["diagnostic_error"])
        self.assertNotIn(session_id, runner.active_sessions)

    def test_completed_finish_replaces_streamed_commentary_with_final_message(self) -> None:
        runner, session_id, job_id = self.make_running_job()

        runner._finish_job(
            job_id,
            "completed",
            session_id,
            "final answer",
            release_session=session_id,
        )

        job = runner.jobs[job_id]
        self.assertEqual("final answer", job["last_message"])
        self.assertEqual("final answer", job["live_text"])

    def test_completed_job_replaces_trailing_commentary_in_session_messages(self) -> None:
        messages = [
            {"role": "user", "ts": 100, "text": "question"},
            {"role": "assistant", "ts": 110, "text": "working update"},
        ]
        job = {
            "status": "completed",
            "created_at": 100,
            "finished_at": 120,
            "last_message": "final answer",
        }

        reconciled = mobile_portal.reconcile_completed_job_message(messages, job)

        self.assertEqual(
            [
                {"role": "user", "ts": 100, "text": "question"},
                {"role": "assistant", "ts": 120, "text": "final answer"},
            ],
            reconciled,
        )

    def test_completed_job_preserves_newer_persisted_assistant_message(self) -> None:
        messages = [
            {"role": "user", "ts": 100, "text": "question"},
            {"role": "assistant", "ts": 130, "text": "newer persisted answer"},
        ]
        job = {
            "status": "completed",
            "created_at": 100,
            "finished_at": 120,
            "last_message": "older job final",
        }

        reconciled = mobile_portal.reconcile_completed_job_message(messages, job)

        self.assertEqual(messages, reconciled)

    def test_completed_job_without_user_message_preserves_existing_history(self) -> None:
        messages = [
            {"role": "assistant", "ts": 90, "text": "older answer"},
        ]
        job = {
            "status": "completed",
            "created_at": 100,
            "finished_at": 120,
            "last_message": "final answer",
        }

        reconciled = mobile_portal.reconcile_completed_job_message(messages, job)

        self.assertEqual(
            [
                {"role": "assistant", "ts": 90, "text": "older answer"},
                {"role": "assistant", "ts": 120, "text": "final answer"},
            ],
            reconciled,
        )


if __name__ == "__main__":
    unittest.main()
