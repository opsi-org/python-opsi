# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

import ctypes
import importlib
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Self

from opsi.exception import OperatingSystemUnsupportedError
from opsi.logging import get_logger
from opsi.system.info import get_system, is_windows

logger = get_logger("opsi")

type RegistryChangeCallback = Callable[[RegistryChangeEvent], None]


class RegistryChangeType(StrEnum):
	"""Registry change type."""

	KEY_ADDED = "key_added"
	KEY_REMOVED = "key_removed"
	VALUE_ADDED = "value_added"
	VALUE_REMOVED = "value_removed"
	VALUE_MODIFIED = "value_modified"


@dataclass(frozen=True)
class RegistryKey:
	"""
	Windows registry key.

	Parameters
	----------
	path : str
		The full registry key path.
	"""

	path: str


@dataclass(frozen=True)
class RegistryValue:
	"""
	Windows registry value.

	Parameters
	----------
	name : str
		The value name. The default value is represented by an empty string.
	data : Any
		The value data.
	value_type : int
		The Windows registry value type.
	"""

	name: str
	data: Any
	value_type: int


@dataclass(frozen=True)
class RegistryChangeEvent:
	"""
	Registry change notification.

	Parameters
	----------
	base_key : str
		The watched registry key.
	changed_key : RegistryKey
		The registry key that changed or contains the changed value.
	changed_value : RegistryValue, optional
		The changed registry value. If None, the change affected the key itself.
	change_type : RegistryChangeType
		The type of registry change.
	timestamp : datetime
		The timestamp when the change notification was received.
	"""

	base_key: str
	changed_key: RegistryKey
	changed_value: RegistryValue | None
	change_type: RegistryChangeType
	timestamp: datetime


type RegistrySnapshot = dict[str, dict[str, RegistryValue]]


class RegistryWatcher:
	"""
	Watch a Windows registry tree for changes.

	The watcher monitors changes to keys and values below the configured base key.
	Windows reports that something changed below the watched key, but not the exact
	changed key or value. Exact change details require additional snapshot and diff
	logic.
	"""

	_REG_NOTIFY_CHANGE_NAME = 0x00000001
	_REG_NOTIFY_CHANGE_LAST_SET = 0x00000004
	_WAIT_OBJECT_0 = 0x00000000
	_WAIT_FAILED = 0xFFFFFFFF
	_INFINITE = 0xFFFFFFFF

	def __init__(self, base_key: str) -> None:
		"""
		Create a registry watcher.

		Parameters
		----------
		base_key : str
			The registry key to watch, for example
			``HKEY_LOCAL_MACHINE\\Software\\Vendor\\Product``.

		"""
		if not is_windows():
			raise OperatingSystemUnsupportedError(f"RegistryWatcher does not support {get_system()}")

		self.base_key = base_key
		self._callbacks: set[RegistryChangeCallback] = set()
		self._callbacks_lock = threading.RLock()
		self._stop_event = threading.Event()
		self._thread: threading.Thread | None = None
		self._stop_handle: int | None = None

	def __enter__(self) -> Self:
		"""
		Start the watcher when entering a context manager.

		Returns
		-------
		RegistryWatcher
			This watcher instance.
		"""
		self.start()
		return self

	def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
		"""
		Stop the watcher when leaving a context manager.

		Parameters
		----------
		exc_type : object
			The exception type, if the context exits with an exception.
		exc_value : object
			The exception value, if the context exits with an exception.
		traceback : object
			The traceback, if the context exits with an exception.
		"""
		self.stop()

	def register_callback(self, callback: RegistryChangeCallback) -> None:
		"""
		Register a callback for registry change events.

		Parameters
		----------
		callback : RegistryChangeCallback
			The callback to run when a registry change is detected.
		"""
		with self._callbacks_lock:
			self._callbacks.add(callback)

	def unregister_callback(self, callback: RegistryChangeCallback) -> None:
		"""
		Unregister a registry change callback.

		Parameters
		----------
		callback : RegistryChangeCallback
			The callback to remove.
		"""
		with self._callbacks_lock:
			self._callbacks.discard(callback)

	def start(self) -> None:
		"""Start watching the registry tree in a background thread."""
		if self._thread and self._thread.is_alive():
			return

		self._stop_event.clear()
		self._thread = threading.Thread(target=self._watch, name=f"RegistryWatcher({self.base_key})", daemon=True)
		self._thread.start()

	def stop(self, timeout: float | None = None) -> None:
		"""
		Stop watching the registry tree.

		Parameters
		----------
		timeout : float, optional
			Maximum time in seconds to wait for the watcher thread to stop.
		"""
		self._stop_event.set()
		if self._stop_handle is not None:
			self._get_kernel32().SetEvent(self._stop_handle)

		if self._thread:
			self._thread.join(timeout)

	def _watch(self) -> None:
		"""Watch the registry key and dispatch callbacks."""
		try:
			self._watch_registry_tree()
		except Exception:
			logger.exception("Registry watcher for %r stopped unexpectedly", self.base_key)

	def _watch_registry_tree(self) -> None:
		"""Run the registry notification loop."""
		winreg = self._get_winreg()
		registry_hive, sub_key = self._parse_base_key(self.base_key, winreg)
		kernel32 = self._get_kernel32()
		advapi32 = self._get_advapi32()

		stop_handle = kernel32.CreateEventW(None, True, False, None)
		change_handle = kernel32.CreateEventW(None, True, False, None)
		self._stop_handle = stop_handle

		registry_snapshot = self._create_snapshot(winreg, registry_hive, sub_key)

		def notify_changes() -> None:
			"""Notify callbacks about all detected registry changes."""
			nonlocal registry_snapshot
			current_snapshot = self._create_snapshot(winreg, registry_hive, sub_key)
			for event in self._diff_snapshots(registry_snapshot, current_snapshot):
				self._notify_callbacks(event)
			registry_snapshot = current_snapshot

		try:
			with winreg.OpenKey(registry_hive, sub_key, 0, winreg.KEY_NOTIFY) as registry_key:
				registry_handle = int(registry_key)
				self._run_notification_loop(advapi32, kernel32, registry_handle, stop_handle, change_handle, notify_changes)
		finally:
			self._stop_handle = None
			kernel32.CloseHandle(change_handle)
			kernel32.CloseHandle(stop_handle)

	def _run_notification_loop(
		self, advapi32: Any, kernel32: Any, registry_handle: int, stop_handle: int, change_handle: int, notify_changes: Callable[[], None]
	) -> None:
		"""Register for registry notifications until the watcher is stopped."""
		while not self._stop_event.is_set():
			kernel32.ResetEvent(change_handle)

			result = advapi32.RegNotifyChangeKeyValue(
				registry_handle,
				True,
				self._REG_NOTIFY_CHANGE_NAME | self._REG_NOTIFY_CHANGE_LAST_SET,
				change_handle,
				True,
			)
			if result:
				self._raise_windows_error(result)

			handles = (ctypes.c_void_p * 2)(stop_handle, change_handle)
			wait_result = kernel32.WaitForMultipleObjects(2, handles, False, self._INFINITE)
			if wait_result == self._WAIT_OBJECT_0:
				return

			if wait_result == self._WAIT_OBJECT_0 + 1:
				notify_changes()
				continue

			if wait_result == self._WAIT_FAILED:
				self._raise_windows_error(kernel32.GetLastError())

			raise RuntimeError(f"Unexpected wait result while watching registry: {wait_result}")

	def _notify_callbacks(self, event: RegistryChangeEvent) -> None:
		"""Notify all registered callbacks."""
		with self._callbacks_lock:
			callbacks = tuple(self._callbacks)

		for callback in callbacks:
			try:
				callback(event)
			except Exception:
				logger.exception("Registry watcher callback failed for %r", self.base_key)

	@classmethod
	def _parse_base_key(cls, base_key: str, winreg: Any) -> tuple[int, str]:
		"""Parse a registry key string into hive and subkey."""
		hive_name, separator, sub_key = base_key.partition("\\")
		if not separator or not sub_key:
			raise ValueError(f"Registry key must include a hive and subkey: {base_key!r}")

		hives = {
			"HKEY_CLASSES_ROOT": winreg.HKEY_CLASSES_ROOT,
			"HKCR": winreg.HKEY_CLASSES_ROOT,
			"HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
			"HKCU": winreg.HKEY_CURRENT_USER,
			"HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
			"HKLM": winreg.HKEY_LOCAL_MACHINE,
			"HKEY_USERS": winreg.HKEY_USERS,
			"HKU": winreg.HKEY_USERS,
			"HKEY_CURRENT_CONFIG": winreg.HKEY_CURRENT_CONFIG,
			"HKCC": winreg.HKEY_CURRENT_CONFIG,
		}

		try:
			return hives[hive_name.upper()], sub_key
		except KeyError as err:
			raise ValueError(f"Unsupported registry hive in key: {base_key!r}") from err

	def _create_snapshot(self, winreg: Any, registry_hive: int, sub_key: str) -> RegistrySnapshot:
		"""Create a snapshot of all keys and values below the watched key."""
		with winreg.OpenKey(registry_hive, sub_key, 0, winreg.KEY_READ) as registry_key:
			return self._read_key_snapshot(winreg, registry_key, self.base_key)

	def _read_key_snapshot(self, winreg: Any, registry_key: Any, key_path: str) -> RegistrySnapshot:
		"""Read a registry key and its descendants into a snapshot."""
		snapshot: RegistrySnapshot = {key_path: self._read_values(winreg, registry_key)}
		for sub_key_name in self._enum_sub_key_names(winreg, registry_key):
			sub_key_path = f"{key_path}\\{sub_key_name}"
			with winreg.OpenKey(registry_key, sub_key_name, 0, winreg.KEY_READ) as sub_key:
				snapshot.update(self._read_key_snapshot(winreg, sub_key, sub_key_path))

		return snapshot

	@staticmethod
	def _read_values(winreg: Any, registry_key: Any) -> dict[str, RegistryValue]:
		"""Read all values from a registry key."""
		values: dict[str, RegistryValue] = {}
		index = 0
		while True:
			try:
				name, data, value_type = winreg.EnumValue(registry_key, index)
			except OSError:
				return values

			values[name] = RegistryValue(name=name, data=data, value_type=value_type)
			index += 1

	@staticmethod
	def _enum_sub_key_names(winreg: Any, registry_key: Any) -> tuple[str, ...]:
		"""Read all subkey names from a registry key."""
		sub_key_names: list[str] = []
		index = 0
		while True:
			try:
				sub_key_names.append(winreg.EnumKey(registry_key, index))
			except OSError:
				return tuple(sub_key_names)

			index += 1

	def _diff_snapshots(self, previous_snapshot: RegistrySnapshot, current_snapshot: RegistrySnapshot) -> tuple[RegistryChangeEvent, ...]:
		"""Create registry change events for the differences between two snapshots."""
		events: list[RegistryChangeEvent] = []
		timestamp = datetime.now(tz=UTC)
		previous_keys = set(previous_snapshot)
		current_keys = set(current_snapshot)

		for key_path in sorted(current_keys - previous_keys):
			events.append(self._create_event(key_path, None, RegistryChangeType.KEY_ADDED, timestamp))
			for value in current_snapshot[key_path].values():
				events.append(self._create_event(key_path, value, RegistryChangeType.VALUE_ADDED, timestamp))

		for key_path in sorted(previous_keys - current_keys):
			for value in previous_snapshot[key_path].values():
				events.append(self._create_event(key_path, value, RegistryChangeType.VALUE_REMOVED, timestamp))
			events.append(self._create_event(key_path, None, RegistryChangeType.KEY_REMOVED, timestamp))

		for key_path in sorted(previous_keys & current_keys):
			previous_values = previous_snapshot[key_path]
			current_values = current_snapshot[key_path]
			previous_value_names = set(previous_values)
			current_value_names = set(current_values)

			for value_name in sorted(current_value_names - previous_value_names):
				events.append(self._create_event(key_path, current_values[value_name], RegistryChangeType.VALUE_ADDED, timestamp))

			for value_name in sorted(previous_value_names - current_value_names):
				events.append(self._create_event(key_path, previous_values[value_name], RegistryChangeType.VALUE_REMOVED, timestamp))

			for value_name in sorted(previous_value_names & current_value_names):
				if previous_values[value_name] != current_values[value_name]:
					events.append(self._create_event(key_path, current_values[value_name], RegistryChangeType.VALUE_MODIFIED, timestamp))

		return tuple(events)

	def _create_event(
		self, key_path: str, changed_value: RegistryValue | None, change_type: RegistryChangeType, timestamp: datetime
	) -> RegistryChangeEvent:
		"""Create a registry change event."""
		return RegistryChangeEvent(
			base_key=self.base_key,
			changed_key=RegistryKey(path=key_path),
			changed_value=changed_value,
			change_type=change_type,
			timestamp=timestamp,
		)

	@staticmethod
	def _get_winreg() -> Any:
		"""Load the Windows registry module."""
		return importlib.import_module("winreg")

	@staticmethod
	def _get_kernel32() -> Any:
		"""Return the Windows kernel32 DLL wrapper."""
		return getattr(ctypes, "windll").kernel32

	@staticmethod
	def _get_advapi32() -> Any:
		"""Return the Windows advapi32 DLL wrapper."""
		return getattr(ctypes, "windll").advapi32

	@staticmethod
	def _raise_windows_error(error_code: int) -> None:
		"""Raise the platform-specific Windows error for an error code."""
		win_error = getattr(ctypes, "WinError", None)
		if callable(win_error):
			raise win_error(error_code)

		raise OSError(error_code, "Windows API call failed")
