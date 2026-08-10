# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import asyncio
import time
from collections.abc import Callable

from opsi.logging import get_logger
from opsi.opsi.messagebus._message import Message

logger = get_logger()


class MessageSender:
	def __init__(self, print_messages: bool = False) -> None:
		self.print_messages = print_messages
		self.messages_sent: list[Message] = []
		self._message_callback_position = 0

	async def send_message(self, message: Message) -> None:
		logger.debug("send_message: %r", message)
		if self.print_messages:
			print(message.to_dict())
		self.messages_sent.append(message)

	async def wait_for_messages(
		self,
		*,
		count: int | None,
		timeout: float = 10.0,
		delay: float = 0.1,
		clear_messages: bool = True,
		error_on_timeout: bool = True,
		true_count: bool = False,
		message_callback: Callable[[Message], bool] | None = None,
	) -> list[Message]:
		"""
		Wait for a certain number of messages to be sent.
		Args:
			count: The number of messages to wait for
				If None, do not wait for a specific number of messages, but wait until the timeout is reached or the message_callback returns True.
			timeout: The maximum time to wait for the messages.
			delay: The delay between checks for new messages.
			clear_messages: Whether to clear the messages after retrieving them.
			error_on_timeout: Whether to raise an error if the timeout is reached.
			true_count: Whether to return exactly the requested number of messages.
			message_callback: A callback function to be called for each new message.
				When the callback returns True, the waiting will stop and the messages will be returned.

		Returns:
			A list of messages.
		"""
		start = time.monotonic()
		while count is None or len(self.messages_sent) < count:
			if message_callback and self._message_callback_position < len(self.messages_sent):
				for message in self.messages_sent[self._message_callback_position :]:
					self._message_callback_position += 1
					if message_callback(message):
						break

			if time.monotonic() - start > timeout:
				if error_on_timeout:
					raise TimeoutError(f"Timeout waiting for {count} messages, got {len(self.messages_sent)}")
				break
			await asyncio.sleep(delay)

		if not clear_messages:
			if not true_count:
				return self.messages_sent
			else:
				return self.messages_sent[0:count]

		if true_count:
			messages = self.messages_sent[0:count].copy()
			self.messages_sent = self.messages_sent[count:].copy()
		else:
			messages = self.messages_sent.copy()
			self.messages_sent = []
		return messages

	async def no_messages(self) -> bool:
		return len(self.messages_sent) == 0
