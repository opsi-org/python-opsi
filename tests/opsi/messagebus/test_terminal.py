# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

"""
messagebus.terminal tests
"""

import asyncio
import os
import re
import time
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from opsi.opsi.messagebus._message import (
	Error,
	Message,
	TerminalCloseEventMessage,
	TerminalCloseRequestMessage,
	TerminalDataReadMessage,
	TerminalDataWriteMessage,
	TerminalErrorMessage,
	TerminalOpenEventMessage,
	TerminalOpenRequestMessage,
)
from opsi.opsi.messagebus._terminal import Terminal, process_terminal_message, start_pty, stop_running_terminals, terminals
from opsi.system.info import is_macos, is_posix, is_windows

from .helper import MessageSender

ANSI_ESCAPE_RE = re.compile(
	r"\x1B(?:"
	r"\[[0-?]*[ -/]*[@-~]"  # CSI
	r"|\][^\x07]*(?:\x07|\x1B\\)"  # OSC
	r")"
)


def test_start_pty_params(tmp_path: Path) -> None:
	str_path = str(tmp_path)
	cols = 150
	rows = 20

	env = {"PATH": os.environ["PATH"], "OPSI_TEST": "foo"}
	(
		pty_pid,
		pty_read,
		pty_write,
		pty_set_size,
		pty_stop,
	) = start_pty(shell="cmd.exe" if is_windows() else "bash", rows=rows, cols=cols, cwd=str_path, env=env)
	assert pty_pid > 0

	time.sleep(2)
	data = b""
	for num in range(10):
		dat = pty_read(4096)
		print("read:", dat)
		data += dat
		if str_path.encode("utf-8") in data:
			break
		if is_macos() and num >= 1:
			break

	command = "cd" if is_windows() else "pwd"
	pty_write(f"{command}\r\n".encode())
	time.sleep(2)
	data = pty_read(4096)

	lines = [ANSI_ESCAPE_RE.sub("", line.strip()) for line in data.decode("utf-8").split("\n")]

	assert lines[0] == command
	assert lines[1].strip().endswith(str_path)

	command = "set" if is_windows() else "env"
	pty_write(f"{command}\r\n".encode())
	data = b""
	for _ in range(30):
		time.sleep(1)
		dat = pty_read(8192)
		print("read:", dat)
		data += dat
		if b"OPSI_TEST=foo" in data:
			if not is_posix():
				break
			if b"TERM=" in data:
				break

	lines = [ANSI_ESCAPE_RE.sub("", line.strip()) for line in data.decode("utf-8").split("\n")]
	assert lines[0] == command
	assert "OPSI_TEST=foo" in lines

	if is_posix():
		assert any(line.startswith("TERM=") for line in lines)

		pty_write(b"stty size\r\n")
		data = b""
		for _ in range(30):
			time.sleep(1)
			dat = pty_read(8192)
			print("read:", dat)
			data += dat
			if b"stty size" in data:
				break
		lines = [line.strip() for line in data.decode("utf-8").split("\n")]
		print("lines:", lines)
		assert any(line.endswith("stty size") for line in lines)
		if not is_macos():
			assert any(f"{rows} {cols}" in line for line in lines)

	pty_set_size(20, 100)
	pty_stop()


def test_start_pty_fail() -> None:
	with pytest.raises(RuntimeError, match="Failed to start pty with shell"):
		start_pty(shell="/will/fail")


async def test_terminal_params() -> None:
	if is_macos():
		pytest.skip("Test currently not implemented on MacOS")

	cols = 150
	rows = 25
	terminal_id = str(uuid.uuid4())
	sender = "service_worker:pytest:1"
	shell = "/bin/bash" if not is_windows() else "cmd.exe"
	env = {"LANG": "de", "OPSI_TEST": "foo"}

	assert not terminals

	message_sender = MessageSender()

	terminal_open_request = TerminalOpenRequestMessage(
		sender="client", back_channel="back_channel", channel="channel", terminal_id=terminal_id, shell=shell, rows=rows, cols=cols, env=env
	)
	await process_terminal_message(message=terminal_open_request, send_message=message_sender.send_message, sender=sender)

	messages = await message_sender.wait_for_messages(count=2)

	assert len(terminals) == 1
	assert isinstance(terminals[terminal_id], Terminal)

	assert isinstance(messages[0], TerminalOpenEventMessage)
	assert messages[0].type == "terminal_open_event"
	assert messages[0].sender == sender
	assert messages[0].channel == "back_channel"
	assert messages[0].terminal_id == terminal_id
	assert messages[0].cols == cols
	assert messages[0].rows == rows

	assert isinstance(messages[1], TerminalDataReadMessage)
	assert messages[1].type == "terminal_data_read"
	assert messages[1].sender == sender
	assert messages[1].channel == "back_channel"
	assert messages[1].terminal_id == terminal_id
	assert messages[1].data

	command = "set" if is_windows() else "env"
	terminal_data_write_message = TerminalDataWriteMessage(
		sender="client", back_channel="back_channel", channel="channel", terminal_id=terminal_id, data=f"{command}\r\n".encode()
	)
	await process_terminal_message(message=terminal_data_write_message, send_message=message_sender.send_message, sender=sender)

	opsi_test_seen, lang_seen, opsi_terminal_id_seen = False, False, False

	def message_callback(message: Message) -> bool:
		nonlocal opsi_test_seen, lang_seen, opsi_terminal_id_seen
		if isinstance(message, TerminalDataReadMessage):
			if b"OPSI_TEST=foo" in message.data:
				opsi_test_seen = True
			if b"LANG=de" in message.data:
				lang_seen = True
			if f"OPSI_TERMINAL_ID={terminal_id}".encode() in message.data:
				opsi_terminal_id_seen = True
			if opsi_test_seen and lang_seen and opsi_terminal_id_seen:
				return True
		return False

	messages = await message_sender.wait_for_messages(count=None, message_callback=message_callback, timeout=30, error_on_timeout=False)
	print("messages:", len(messages))
	data = b""
	for message in messages:
		assert isinstance(message, TerminalDataReadMessage)
		data += message.data
	lines = data.decode("utf-8").split("\r\n")
	for line in lines:
		print("line:", line)

	assert "OPSI_TEST=foo" in lines
	assert "LANG=de" in lines
	assert f"OPSI_TERMINAL_ID={terminal_id}" in lines

	if is_posix():
		terminal_data_write_message = TerminalDataWriteMessage(
			sender="client", back_channel="back_channel", channel="channel", terminal_id=terminal_id, data=b"stty size\r\n"
		)
		await process_terminal_message(message=terminal_data_write_message, send_message=message_sender.send_message, sender=sender)

		messages = await message_sender.wait_for_messages(count=2)

		assert isinstance(messages[0], TerminalDataReadMessage)
		assert messages[0].type == "terminal_data_read"
		assert messages[0].sender == sender
		assert messages[0].channel == "back_channel"
		assert messages[0].terminal_id == terminal_id
		lines = messages[0].data.decode("utf-8").split("\r\n")
		assert lines[0] == "stty size"

		assert isinstance(messages[1], TerminalDataReadMessage)
		assert f"{rows} {cols}" in messages[1].data.decode("utf-8")

	# Reopen terminal
	cols = 160
	rows = 30
	terminal_open_request = TerminalOpenRequestMessage(
		sender="client", back_channel="back_channel", channel="channel", terminal_id=terminal_id, shell=shell, rows=rows, cols=cols
	)
	await process_terminal_message(message=terminal_open_request, send_message=message_sender.send_message, sender=sender)

	messages = await message_sender.wait_for_messages(count=1)

	assert len(terminals) == 1
	assert isinstance(terminals[terminal_id], Terminal)

	assert isinstance(messages[0], TerminalOpenEventMessage)
	assert messages[0].type == "terminal_open_event"
	assert messages[0].sender == sender
	assert messages[0].channel == "back_channel"
	assert messages[0].terminal_id == terminal_id
	assert messages[0].cols == cols
	assert messages[0].rows == rows

	for message in await message_sender.wait_for_messages(count=10, timeout=3, error_on_timeout=False):
		assert isinstance(message, TerminalDataReadMessage)

	terminal_close_request = TerminalCloseRequestMessage(
		sender="client", back_channel="back_channel", channel="channel", terminal_id=terminal_id
	)
	await process_terminal_message(message=terminal_close_request, send_message=message_sender.send_message, sender=sender)
	messages = await message_sender.wait_for_messages(count=1)

	assert isinstance(messages[0], TerminalCloseEventMessage)
	assert messages[0].type == "terminal_close_event"
	assert messages[0].sender == sender
	assert messages[0].channel == "back_channel"
	assert messages[0].terminal_id == terminal_id

	if is_windows():
		await asyncio.sleep(3)


async def test_terminal_timeout() -> None:
	terminal_id = str(uuid.uuid4())
	sender = "service_worker:pytest:1"

	assert not terminals

	message_sender = MessageSender()

	terminal_open_request = TerminalOpenRequestMessage(
		sender="client", back_channel="back_channel", channel="channel", terminal_id=terminal_id
	)
	with patch("opsi.opsi.messagebus._terminal.Terminal.idle_timeout", 3):
		await process_terminal_message(message=terminal_open_request, send_message=message_sender.send_message, sender=sender)
		messages = await message_sender.wait_for_messages(count=10, timeout=8, error_on_timeout=False)
		assert isinstance(messages[-1], TerminalCloseEventMessage)


async def test_terminal_fail() -> None:
	terminal_id = str(uuid.uuid4())

	message_sender = MessageSender(print_messages=True)

	terminal_open_request = TerminalOpenRequestMessage(
		sender="client", back_channel="back_channel", channel="channel", terminal_id=terminal_id, shell="/fail/shell"
	)
	await process_terminal_message(message=terminal_open_request, send_message=message_sender.send_message)

	messages = await message_sender.wait_for_messages(count=2)

	assert len(messages) == 2
	assert isinstance(messages[0], TerminalErrorMessage)
	assert messages[0].channel == "back_channel"
	assert messages[0].terminal_id == terminal_id
	assert messages[0].error == Error(
		message=(
			"Failed to create new terminal: Failed to start pty with shell '/fail/shell': "
			"The command was not found or was not executable: /fail/shell."
		)
	)

	assert isinstance(messages[1], TerminalCloseEventMessage)
	assert messages[1].channel == "back_channel"
	assert messages[1].terminal_id == terminal_id

	await asyncio.sleep(1)
	terminal_id = str(uuid.uuid4())

	shell = 'cmd.exe /c "echo exit_1 && exit 1"' if is_windows() else 'bash -c "echo exit_1 && exit 1"'
	terminal_open_request = TerminalOpenRequestMessage(
		sender="client", back_channel="back_channel", channel="channel", terminal_id=terminal_id, shell=shell
	)
	await process_terminal_message(message=terminal_open_request, send_message=message_sender.send_message)

	messages = await message_sender.wait_for_messages(count=10, timeout=10, error_on_timeout=False)

	assert len(messages) >= 3
	assert isinstance(messages[0], TerminalOpenEventMessage)
	data = b""
	for idx in range(1, len(messages) - 1):
		msg = messages[idx]
		assert isinstance(msg, TerminalDataReadMessage)
		data += msg.data

	data_str = ANSI_ESCAPE_RE.sub("", data.decode("utf-8")).replace(" ", "")
	assert data_str == "exit_1\r\n"
	assert isinstance(messages[-1], TerminalCloseEventMessage)


async def test_multiple_terminals() -> None:
	terminal1_id = str(uuid.uuid4())
	terminal2_id = str(uuid.uuid4())
	terminal3_id = str(uuid.uuid4())
	sender = "service_worker:pytest:1"

	assert not terminals

	message_sender = MessageSender()

	for terminal_id in (terminal1_id, terminal2_id, terminal3_id):
		terminal_open_request = TerminalOpenRequestMessage(sender="client", channel="channel", terminal_id=terminal_id)
		await process_terminal_message(message=terminal_open_request, send_message=message_sender.send_message, sender=sender)

	await asyncio.sleep(1)

	for terminal_id in (terminal1_id, terminal2_id, terminal3_id):
		terminal_data_write_message = TerminalDataWriteMessage(
			sender="client", channel="channel", terminal_id=terminal_id, data=b"echo test\r\n"
		)
		await process_terminal_message(message=terminal_data_write_message, send_message=message_sender.send_message, sender=sender)

	await asyncio.sleep(1)

	for terminal_id in (terminal1_id, terminal2_id, terminal3_id):
		terminal_close_request = TerminalCloseRequestMessage(sender="client", channel="channel", terminal_id=terminal_id)
		await process_terminal_message(message=terminal_close_request, send_message=message_sender.send_message, sender=sender)

	messages = await message_sender.wait_for_messages(count=100, timeout=5, error_on_timeout=False)
	for terminal_id in (terminal1_id, terminal2_id, terminal3_id):
		assert any(isinstance(m, TerminalOpenEventMessage) and m.terminal_id == terminal_id for m in messages)
		assert any(isinstance(m, TerminalDataReadMessage) and m.terminal_id == terminal_id for m in messages)
		assert any(isinstance(m, TerminalCloseEventMessage) and m.terminal_id == terminal_id for m in messages)


async def test_stop_running_terminals() -> None:
	fork_delay_original = Terminal.fork_delay
	Terminal.fork_delay = 3.0
	try:
		message_sender = MessageSender()

		terminal_id = str(uuid.uuid4())
		shell = "timeout /t 10" if is_windows() else "sleep 10"

		terminal_open_request = TerminalOpenRequestMessage(
			sender="client", back_channel="back_channel", channel="channel", terminal_id=terminal_id, shell=shell
		)
		await process_terminal_message(terminal_open_request, send_message=message_sender.send_message)

		messages = await message_sender.wait_for_messages(count=1)
		assert len(messages) == 1
		assert isinstance(messages[0], TerminalOpenEventMessage)

		assert len(terminals) == 1
		assert terminals[terminal_open_request.terminal_id]

		await stop_running_terminals()

		messages: list = await message_sender.wait_for_messages(count=1)
		terminal_close_message = messages[-1]
		assert isinstance(terminal_close_message, TerminalCloseEventMessage)
		assert terminal_close_message.terminal_id == terminal_id
	finally:
		Terminal.fork_delay = fork_delay_original
