# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

import importlib
import sys
from types import ModuleType
from typing import Iterable

import pytest


def _load_windows_module(
	monkeypatch: pytest.MonkeyPatch,
	*,
	events: Iterable[str],
	xml_map: dict[str, str],
) -> ModuleType:
	fake_win32evtlog = ModuleType("win32evtlog")
	fake_win32evtlog.EvtQueryReverseDirection = 1  # ty: ignore[unresolved-attribute]
	fake_win32evtlog.EvtQueryChannelPath = 2  # ty: ignore[unresolved-attribute]
	fake_win32evtlog.EvtRenderEventXml = 3  # ty: ignore[unresolved-attribute]

	def _evt_query(*, Path: str, Flags: int, Query: str) -> object:
		return {
			"path": Path,
			"flags": Flags,
			"query": Query,
		}

	def _evt_next(handle: object, *, Count: int, Timeout: int) -> list[str]:
		return list(events)

	def _evt_render(event: str, render_flag: int) -> str:
		return xml_map[event]

	fake_win32evtlog.EvtQuery = _evt_query  # ty: ignore[unresolved-attribute]
	fake_win32evtlog.EvtNext = _evt_next  # ty: ignore[unresolved-attribute]
	fake_win32evtlog.EvtRender = _evt_render  # ty: ignore[unresolved-attribute]

	monkeypatch.setitem(sys.modules, "win32evtlog", fake_win32evtlog)
	sys.modules.pop("opsi.system.update._windows", None)
	return importlib.import_module("opsi.system.update._windows")


@pytest.mark.windows
def test_updates_running_returns_false_when_no_events(monkeypatch: pytest.MonkeyPatch) -> None:
	module = _load_windows_module(monkeypatch, events=[], xml_map={})
	assert module.updates_running() is False


@pytest.mark.windows
def test_updates_running_returns_true_for_start_event(monkeypatch: pytest.MonkeyPatch) -> None:
	module = _load_windows_module(
		monkeypatch,
		events=["event"],
		xml_map={"event": "<Event><EventId>43</EventId></Event>"},
	)
	assert module.updates_running() is True


@pytest.mark.windows
@pytest.mark.parametrize("event_id", [44, 19, 20])
def test_updates_running_returns_false_for_terminal_events(
	monkeypatch: pytest.MonkeyPatch,
	event_id: int,
) -> None:
	module = _load_windows_module(
		monkeypatch,
		events=["event"],
		xml_map={"event": f"<Event><EventId>{event_id}</EventId></Event>"},
	)
	assert module.updates_running() is False


@pytest.mark.windows
def test_updates_running_skips_events_without_ids(monkeypatch: pytest.MonkeyPatch) -> None:
	module = _load_windows_module(
		monkeypatch,
		events=["event"],
		xml_map={"event": "<Event><EventId></EventId></Event>"},
	)
	assert module.updates_running() is False
