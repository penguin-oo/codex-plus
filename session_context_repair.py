import json
import re
import shutil
import sqlite3
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


MAX_RESUMABLE_SESSION_FILE_BYTES = 50 * 1024 * 1024
MAX_HISTORY_SUMMARY_ENTRIES = 12
MAX_HISTORY_ENTRY_CHARS = 500
AUTH_PROVIDER_REPAIR_BACKUP_MARKER = ".auth-provider-backup-"
AUTH_PROVIDER_REPAIR_STATE_SUFFIX = ".auth-provider-repair.json"
INVALID_ENCRYPTED_ITEM_PATTERN = re.compile(r"\brs_[A-Za-z0-9_-]+\b")


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _backup_suffix() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _json_line(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _truncate_text(text: str, limit: int = MAX_HISTORY_ENTRY_CHARS) -> str:
    clean = " ".join(str(text).split())
    if len(clean) <= limit:
        return clean
    return f"{clean[: max(0, limit - 3)]}..."


def _auth_provider_repair_state_path(path: Path) -> Path:
    return path.with_name(f"{path.name}{AUTH_PROVIDER_REPAIR_STATE_SUFFIX}")


def _auth_provider_repair_state_is_current(path: Path, stat_result: object) -> bool:
    state_path = _auth_provider_repair_state_path(path)
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        return (
            isinstance(state, dict)
            and int(state.get("source_mtime_ns", -1)) == int(getattr(stat_result, "st_mtime_ns", -2))
            and int(state.get("source_size", -1)) == int(getattr(stat_result, "st_size", -2))
        )
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return False


def _is_encrypted_reasoning_item(value: object) -> bool:
    return (
        isinstance(value, dict)
        and str(value.get("type", "")).strip() == "reasoning"
        and bool(value.get("encrypted_content"))
    )


def _invalid_encrypted_error(value: object) -> bool:
    try:
        serialized = json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        serialized = str(value)
    return "invalid_encrypted_content" in serialized


def _invalid_item_ids(value: object) -> set[str]:
    try:
        serialized = json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        serialized = str(value)
    return set(INVALID_ENCRYPTED_ITEM_PATTERN.findall(serialized))


def _rollout_projection_cursor(path: Path) -> tuple[int, int] | None:
    try:
        file_size = path.stat().st_size
        with path.open("rb") as handle:
            position = file_size
            buffered = b""
            while position > 0:
                chunk_size = min(64 * 1024, position)
                position -= chunk_size
                handle.seek(position)
                buffered = handle.read(chunk_size) + buffered
                lines = buffered.splitlines()
                if position > 0 and lines:
                    buffered = lines.pop(0)
                for raw_line in reversed(lines):
                    try:
                        item = json.loads(raw_line.decode("utf-8"))
                    except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
                        continue
                    ordinal = item.get("ordinal") if isinstance(item, dict) else None
                    if isinstance(ordinal, int):
                        return file_size, ordinal + 1
            if buffered:
                try:
                    item = json.loads(buffered.decode("utf-8"))
                except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
                    item = None
                ordinal = item.get("ordinal") if isinstance(item, dict) else None
                if isinstance(ordinal, int):
                    return file_size, ordinal + 1
    except OSError:
        return None
    return None


def _repair_thread_history_projection(
    session_id: str,
    database_file: Path | None,
    *,
    invalid_turn_ids: set[str],
    invalid_item_ids: set[str],
    session_file: Path | None = None,
) -> None:
    if database_file is None or not database_file.exists():
        return
    connection = sqlite3.connect(database_file, timeout=5.0)
    try:
        rows = connection.execute(
            "SELECT turn_id, error_json FROM thread_turns "
            "WHERE thread_id=? AND error_json LIKE '%invalid_encrypted_content%'",
            (session_id,),
        ).fetchall()
        for turn_id, error_json in rows:
            invalid_turn_ids.add(str(turn_id))
            invalid_item_ids.update(_invalid_item_ids(error_json))
        if invalid_item_ids:
            placeholders = ",".join("?" for _ in invalid_item_ids)
            connection.execute(
                f"DELETE FROM thread_items WHERE thread_id=? AND item_id IN ({placeholders})",
                (session_id, *sorted(invalid_item_ids)),
            )
        if invalid_turn_ids:
            placeholders = ",".join("?" for _ in invalid_turn_ids)
            connection.execute(
                f"UPDATE thread_turns SET status='completed', error_json=NULL "
                f"WHERE thread_id=? AND turn_id IN ({placeholders})",
                (session_id, *sorted(invalid_turn_ids)),
            )
        cursor = _rollout_projection_cursor(session_file) if session_file is not None else None
        projection_table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='thread_history_projection_state'"
        ).fetchone()
        if cursor is not None and projection_table:
            connection.execute(
                "INSERT INTO thread_history_projection_state "
                "(thread_id, next_rollout_byte_offset, next_rollout_ordinal) VALUES (?, ?, ?) "
                "ON CONFLICT(thread_id) DO UPDATE SET "
                "next_rollout_byte_offset=excluded.next_rollout_byte_offset, "
                "next_rollout_ordinal=excluded.next_rollout_ordinal",
                (session_id, cursor[0], cursor[1]),
            )
        connection.commit()
    finally:
        connection.close()


def clear_invalid_encrypted_content_history(
    session_id: str,
    session_file: Path,
    *,
    thread_history_db: Path | None = None,
) -> Path | None:
    """Hide stale cross-provider decryption failures without touching valid reasoning."""
    path = Path(session_file)
    if not session_id or not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8", errors="ignore", newline="") as source:
            first_line = source.readline().rstrip("\r\n")
    except OSError:
        return None
    try:
        first_item = json.loads(first_line)
    except (ValueError, json.JSONDecodeError):
        return None
    first_payload = first_item.get("payload", {}) if isinstance(first_item, dict) else {}
    if (
        not isinstance(first_item, dict)
        or first_item.get("type") != "session_meta"
        or not isinstance(first_payload, dict)
        or str(first_payload.get("id", "")).strip() != session_id
    ):
        return None

    temp_path = path.with_name(f"{path.name}.invalid-encrypted-repairing")
    invalid_turn_ids: set[str] = set()
    invalid_item_ids: set[str] = set()
    changed_lines = 0
    try:
        temp_path.unlink(missing_ok=True)
        with (
            path.open("r", encoding="utf-8", errors="ignore", newline="") as source,
            temp_path.open("w", encoding="utf-8", newline="") as target,
        ):
            for raw_line in source:
                try:
                    item = json.loads(raw_line)
                except (ValueError, json.JSONDecodeError):
                    target.write(raw_line)
                    continue
                payload = item.get("payload") if isinstance(item, dict) else None
                if (
                    isinstance(item, dict)
                    and item.get("type") == "event_msg"
                    and isinstance(payload, dict)
                    and payload.get("type") == "task_complete"
                    and _invalid_encrypted_error(payload.get("error"))
                ):
                    invalid_turn_ids.add(str(payload.get("turn_id", "")).strip())
                    invalid_item_ids.update(_invalid_item_ids(payload.get("error")))
                    changed_payload = dict(payload)
                    changed_payload["error"] = None
                    item = dict(item)
                    item["payload"] = changed_payload
                    target.write(json.dumps(item, ensure_ascii=False) + "\n")
                    changed_lines += 1
                    continue
                target.write(raw_line)
    except OSError:
        temp_path.unlink(missing_ok=True)
        return None

    backup_path: Path | None = None
    try:
        if changed_lines:
            backup_path = path.with_name(
                f"{path.name}{AUTH_PROVIDER_REPAIR_BACKUP_MARKER}{_backup_suffix()}.jsonl"
            )
            shutil.copy2(path, backup_path)
            temp_path.replace(path)
        else:
            temp_path.unlink(missing_ok=True)
        _repair_thread_history_projection(
            session_id,
            thread_history_db,
            invalid_turn_ids=invalid_turn_ids,
            invalid_item_ids=invalid_item_ids,
            session_file=path,
        )
    except (OSError, sqlite3.Error):
        temp_path.unlink(missing_ok=True)
        return None
    return backup_path


def repair_session_for_codex_auth(
    session_id: str,
    session_file: Path,
    *,
    thread_history_db: Path | None = None,
) -> Path | None:
    """Remove provider-specific encrypted reasoning before official-auth resume.

    The original file is copied before replacement. Visible messages and all
    non-encrypted session events remain unchanged.
    """
    path = Path(session_file)
    if not session_id or not path.exists():
        return None
    try:
        source_stat = path.stat()
        with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
            first_line = handle.readline().rstrip("\r\n")
    except OSError:
        return None
    if _auth_provider_repair_state_is_current(path, source_stat):
        return None
    try:
        first_item = json.loads(first_line)
    except (ValueError, json.JSONDecodeError):
        return None
    first_payload = first_item.get("payload", {}) if isinstance(first_item, dict) else {}
    if (
        not isinstance(first_item, dict)
        or first_item.get("type") != "session_meta"
        or not isinstance(first_payload, dict)
        or str(first_payload.get("id", "")).strip() != session_id
    ):
        return None

    temp_path = path.with_name(f"{path.name}.auth-provider-repairing")
    removed_items = 0
    changed_event_lines = 0
    invalid_item_ids: set[str] = set()
    try:
        temp_path.unlink(missing_ok=True)
        with (
            path.open("r", encoding="utf-8", errors="ignore", newline="") as source,
            temp_path.open("w", encoding="utf-8", newline="") as target,
        ):
            for raw_line in source:
                try:
                    item = json.loads(raw_line)
                except (ValueError, json.JSONDecodeError):
                    target.write(raw_line)
                    continue

                payload = item.get("payload") if isinstance(item, dict) else None
                if (
                    isinstance(item, dict)
                    and item.get("type") == "response_item"
                    and _is_encrypted_reasoning_item(payload)
                ):
                    invalid_item_ids.add(str(payload.get("id", "")).strip())
                    removed_items += 1
                    continue

                if isinstance(item, dict) and item.get("type") == "event_msg" and isinstance(payload, dict):
                    nested_item = payload.get("item")
                    if _is_encrypted_reasoning_item(nested_item):
                        changed_payload = dict(payload)
                        changed_item = dict(nested_item)
                        changed_item.pop("encrypted_content", None)
                        changed_payload["item"] = changed_item
                        item = dict(item)
                        item["payload"] = changed_payload
                        changed_event_lines += 1
                        target.write(json.dumps(item, ensure_ascii=False) + "\n")
                        continue
                target.write(raw_line)
    except (OSError, ValueError):
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        return None

    if not removed_items and not changed_event_lines:
        try:
            temp_path.unlink(missing_ok=True)
            current_stat = path.stat()
            _auth_provider_repair_state_path(path).write_text(
                json.dumps(
                    {
                        "session_id": session_id,
                        "source_mtime_ns": current_stat.st_mtime_ns,
                        "source_size": current_stat.st_size,
                        "removed_items": 0,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        except OSError:
            pass
        return None

    backup_path = path.with_name(
        f"{path.name}{AUTH_PROVIDER_REPAIR_BACKUP_MARKER}{_backup_suffix()}.jsonl"
    )
    try:
        shutil.copy2(path, backup_path)
        temp_path.replace(path)
        repaired_stat = path.stat()
        _auth_provider_repair_state_path(path).write_text(
            json.dumps(
                {
                    "session_id": session_id,
                    "source_mtime_ns": repaired_stat.st_mtime_ns,
                    "source_size": repaired_stat.st_size,
                    "removed_items": removed_items,
                    "changed_event_lines": changed_event_lines,
                    "backup": backup_path.name,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        _repair_thread_history_projection(
            session_id,
            thread_history_db,
            invalid_turn_ids=set(),
            invalid_item_ids={item_id for item_id in invalid_item_ids if item_id},
            session_file=path,
        )
    except (OSError, sqlite3.Error):
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        return None
    return backup_path


def recent_history_entries(
    session_id: str,
    history_file: Path,
    *,
    max_entries: int = MAX_HISTORY_SUMMARY_ENTRIES,
) -> list[str]:
    if not history_file.exists() or max_entries <= 0:
        return []
    entries: deque[str] = deque(maxlen=max_entries)
    try:
        with history_file.open("r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                try:
                    item = json.loads(line)
                except (ValueError, json.JSONDecodeError):
                    continue
                if not isinstance(item, dict) or str(item.get("session_id", "")).strip() != session_id:
                    continue
                text = _truncate_text(str(item.get("text", "")).strip())
                if text:
                    entries.append(text)
    except OSError:
        return []
    return list(entries)


def _build_summary(entries: Iterable[str], backup_path: Path) -> str:
    lines = [
        "[历史摘要 / compacted because the original rollout exceeded the model context window]",
        "这条会话的原始 rollout 太大，继续恢复会超过模型上下文窗口；程序已先备份原文件，再保留最近历史摘要。",
        f"完整备份文件名：{backup_path.name}",
    ]
    recent = [entry for entry in entries if entry]
    if recent:
        lines.append("最近的用户历史：")
        for entry in recent:
            lines.append(f"- {entry}")
    return "\n".join(lines)


def compact_oversized_session_file(
    session_id: str,
    session_file: Path,
    history_file: Path,
    *,
    max_bytes: int = MAX_RESUMABLE_SESSION_FILE_BYTES,
) -> Path | None:
    path = Path(session_file)
    if not session_id or not path.exists():
        return None
    try:
        if path.stat().st_size <= max_bytes:
            return None
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            first_line = handle.readline().rstrip("\n")
    except OSError:
        return None
    if not first_line:
        return None
    try:
        first_item = json.loads(first_line)
    except (ValueError, json.JSONDecodeError):
        return None
    if (
        not isinstance(first_item, dict)
        or first_item.get("type") != "session_meta"
        or str(first_item.get("payload", {}).get("id", "")).strip() != session_id
    ):
        return None

    backup_path = path.with_name(f"{path.name}.context-overflow-backup-{_backup_suffix()}.jsonl")
    try:
        shutil.copy2(path, backup_path)
    except OSError:
        return None

    entries = recent_history_entries(session_id, Path(history_file))
    now = _utc_timestamp()
    lines = [
        first_line,
        _json_line(
            {
                "timestamp": now,
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": _build_summary(entries, backup_path)}],
                },
            }
        ),
        _json_line(
            {
                "timestamp": now,
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "已载入瘦身后的历史摘要。"}],
                },
            }
        ),
    ]
    if entries:
        lines.append(
            _json_line(
                {
                    "timestamp": now,
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": entries[-1]}],
                    },
                }
            )
        )

    temp_path = path.with_name(f"{path.name}.repairing")
    try:
        temp_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        temp_path.replace(path)
    except OSError:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        return None
    return backup_path
