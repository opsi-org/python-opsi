# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

from datetime import UTC, datetime
from types import ModuleType
from typing import Any, cast

import pytest

from opsi.exception import OperatingSystemUnsupportedError
from opsi.system.registry import RegistryChangeEvent, RegistryChangeType, RegistryKey, RegistryValue, RegistryWatcher


@pytest.fixture
def winreg() -> ModuleType:
	winreg_module = ModuleType("winreg")
	cast(Any, winreg_module).HKEY_CLASSES_ROOT = 1
	cast(Any, winreg_module).HKEY_CURRENT_USER = 2
	cast(Any, winreg_module).HKEY_LOCAL_MACHINE = 3
	cast(Any, winreg_module).HKEY_USERS = 4
	cast(Any, winreg_module).HKEY_CURRENT_CONFIG = 5
	return winreg_module


@pytest.fixture
def registry_watcher(monkeypatch: pytest.MonkeyPatch) -> RegistryWatcher:
	monkeypatch.setattr("opsi.system.registry._registry_watcher.get_system", lambda: "Windows")
	monkeypatch.setattr("opsi.system.registry._registry_watcher.is_windows", lambda: True)
	return RegistryWatcher(r"HKEY_LOCAL_MACHINE\Software\opsi")


@pytest.fixture
def registry_change_event(registry_watcher: RegistryWatcher) -> RegistryChangeEvent:
	return RegistryChangeEvent(
		base_key=registry_watcher.base_key,
		changed_key=RegistryKey(path=registry_watcher.base_key),
		changed_value=RegistryValue(name="Value", data="data", value_type=1),
		change_type=RegistryChangeType.VALUE_MODIFIED,
		timestamp=datetime(2026, 4, 30, tzinfo=UTC),
	)


def test_registry_watcher_raises_on_non_windows(monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setattr("opsi.system.registry._registry_watcher.get_system", lambda: "Linux")
	monkeypatch.setattr("opsi.system.registry._registry_watcher.is_windows", lambda: False)

	with pytest.raises(OperatingSystemUnsupportedError, match="RegistryWatcher does not support Linux"):
		RegistryWatcher(r"HKEY_LOCAL_MACHINE\Software\opsi")


@pytest.mark.parametrize(
	("base_key", "expected_hive", "expected_sub_key"),
	[
		(r"HKEY_LOCAL_MACHINE\Software\opsi", 3, r"Software\opsi"),
		(r"HKLM\Software\opsi", 3, r"Software\opsi"),
		(r"HKEY_CURRENT_USER\Software\opsi", 2, r"Software\opsi"),
		(r"HKCU\Software\opsi", 2, r"Software\opsi"),
		(r"HKEY_USERS\.DEFAULT", 4, ".DEFAULT"),
	],
)
def test_parse_base_key_returns_hive_and_sub_key(base_key: str, expected_hive: int, expected_sub_key: str, winreg: ModuleType) -> None:
	registry_hive, sub_key = RegistryWatcher._parse_base_key(base_key, winreg)

	assert registry_hive == expected_hive
	assert sub_key == expected_sub_key


@pytest.mark.parametrize("base_key", ["", "HKEY_LOCAL_MACHINE", "HKEY_LOCAL_MACHINE\\", r"UNKNOWN\Software"])
def test_parse_base_key_raises_on_invalid_key(base_key: str, winreg: ModuleType) -> None:
	with pytest.raises(ValueError):
		RegistryWatcher._parse_base_key(base_key, winreg)


def test_register_callback_is_idempotent(registry_watcher: RegistryWatcher, registry_change_event: RegistryChangeEvent) -> None:
	events: list[RegistryChangeEvent] = []

	def callback(event: RegistryChangeEvent) -> None:
		events.append(event)

	registry_watcher.register_callback(callback)
	registry_watcher.register_callback(callback)
	registry_watcher._notify_callbacks(registry_change_event)

	assert len(events) == 1
	assert events[0] == registry_change_event


def test_unregister_callback_removes_callback(registry_watcher: RegistryWatcher, registry_change_event: RegistryChangeEvent) -> None:
	events: list[RegistryChangeEvent] = []

	def callback(event: RegistryChangeEvent) -> None:
		events.append(event)

	registry_watcher.register_callback(callback)
	registry_watcher.unregister_callback(callback)
	registry_watcher._notify_callbacks(registry_change_event)

	assert events == []


def test_callback_exception_does_not_stop_other_callbacks(
	registry_watcher: RegistryWatcher, registry_change_event: RegistryChangeEvent
) -> None:
	events: list[RegistryChangeEvent] = []

	def failing_callback(event: RegistryChangeEvent) -> None:
		raise RuntimeError("Callback failed")

	def working_callback(event: RegistryChangeEvent) -> None:
		events.append(event)

	registry_watcher.register_callback(failing_callback)
	registry_watcher.register_callback(working_callback)
	registry_watcher._notify_callbacks(registry_change_event)

	assert len(events) == 1
	assert events[0] == registry_change_event


def test_diff_snapshots_reports_modified_value(registry_watcher: RegistryWatcher) -> None:
	previous_snapshot = {registry_watcher.base_key: {"Value": RegistryValue(name="Value", data="old", value_type=1)}}
	current_snapshot = {registry_watcher.base_key: {"Value": RegistryValue(name="Value", data="new", value_type=1)}}

	events = registry_watcher._diff_snapshots(previous_snapshot, current_snapshot)

	assert len(events) == 1
	assert events[0].base_key == registry_watcher.base_key
	assert events[0].changed_key == RegistryKey(path=registry_watcher.base_key)
	assert events[0].changed_value == RegistryValue(name="Value", data="new", value_type=1)
	assert events[0].change_type == RegistryChangeType.VALUE_MODIFIED
	assert events[0].timestamp.tzinfo == UTC


def test_diff_snapshots_reports_added_key_and_value(registry_watcher: RegistryWatcher) -> None:
	changed_key_path = f"{registry_watcher.base_key}\\NewKey"
	previous_snapshot = {registry_watcher.base_key: {}}
	current_snapshot = {
		registry_watcher.base_key: {},
		changed_key_path: {"Value": RegistryValue(name="Value", data="data", value_type=1)},
	}

	events = registry_watcher._diff_snapshots(previous_snapshot, current_snapshot)

	assert [(event.changed_key.path, event.changed_value, event.change_type) for event in events] == [
		(changed_key_path, None, RegistryChangeType.KEY_ADDED),
		(changed_key_path, RegistryValue(name="Value", data="data", value_type=1), RegistryChangeType.VALUE_ADDED),
	]


def test_notification_loop_registers_subtree_watch_and_notifies_callback(registry_watcher: RegistryWatcher) -> None:
	notification_count = 0

	class Advapi32:
		def __init__(self) -> None:
			self.calls: list[tuple[int, bool, int, int, bool]] = []

		def RegNotifyChangeKeyValue(
			self, registry_handle: int, watch_subtree: bool, notify_filter: int, event: int, asynchronous: bool
		) -> int:
			self.calls.append((registry_handle, watch_subtree, notify_filter, event, asynchronous))
			return 0

	class Kernel32:
		def __init__(self) -> None:
			self.wait_results = [registry_watcher._WAIT_OBJECT_0 + 1, registry_watcher._WAIT_OBJECT_0]

		def ResetEvent(self, event: int) -> None:
			assert event == 2

		def WaitForMultipleObjects(self, count: int, handles: object, wait_all: bool, milliseconds: int) -> int:
			assert count == 2
			assert wait_all is False
			assert milliseconds == registry_watcher._INFINITE
			return self.wait_results.pop(0)

	def notify_changes() -> None:
		nonlocal notification_count
		notification_count += 1

	advapi32 = Advapi32()
	registry_watcher._run_notification_loop(advapi32, Kernel32(), 10, 1, 2, notify_changes)

	assert notification_count == 1
	assert advapi32.calls == [
		(10, True, registry_watcher._REG_NOTIFY_CHANGE_NAME | registry_watcher._REG_NOTIFY_CHANGE_LAST_SET, 2, True),
		(10, True, registry_watcher._REG_NOTIFY_CHANGE_NAME | registry_watcher._REG_NOTIFY_CHANGE_LAST_SET, 2, True),
	]


def test_start_is_idempotent(registry_watcher: RegistryWatcher, monkeypatch: pytest.MonkeyPatch) -> None:
	started_threads: list[object] = []

	class Thread:
		def __init__(self, **kwargs: object) -> None:
			self.kwargs = kwargs

		def is_alive(self) -> bool:
			return True

		def start(self) -> None:
			started_threads.append(self)

	monkeypatch.setattr("opsi.system.registry._registry_watcher.threading.Thread", Thread)

	registry_watcher.start()
	registry_watcher.start()

	assert len(started_threads) == 1


def test_context_manager_starts_and_stops_watcher(registry_watcher: RegistryWatcher, monkeypatch: pytest.MonkeyPatch) -> None:
	started = False
	stopped = False

	def start() -> None:
		nonlocal started
		started = True

	def stop(timeout: float | None = None) -> None:
		nonlocal stopped
		stopped = True
		assert timeout is None

	monkeypatch.setattr(registry_watcher, "start", start)
	monkeypatch.setattr(registry_watcher, "stop", stop)

	with registry_watcher as context_watcher:
		assert context_watcher is registry_watcher

	assert started is True
	assert stopped is True
