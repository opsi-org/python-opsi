# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import asyncio
import time

from opsi.logging import get_logger
from opsi.messagebus.message import Message

logger = get_logger()


class MessageSender:
	def __init__(self, print_messages: bool = False) -> None:
		self.print_messages = print_messages
		self.messages_sent: list[Message] = []

	async def send_message(self, message: Message) -> None:
		logger.debug("send_message: %r", message)
		if self.print_messages:
			print(message.to_dict())
		self.messages_sent.append(message)

	async def wait_for_messages(
		self,
		count: int,
		timeout: float = 10.0,
		delay: float = 0.1,
		clear_messages: bool = True,
		error_on_timeout: bool = True,
		true_count: bool = False,
	) -> list[Message]:
		start = time.monotonic()
		while len(self.messages_sent) < count:
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
