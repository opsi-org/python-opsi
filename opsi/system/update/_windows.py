# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from xml.dom import minidom

import win32evtlog  # type: ignore[import]

from opsi.logging import get_logger

logger = get_logger("opsi")


def updates_running() -> bool:
	# TODO: This is currently not working, because the eventlog toes not contain these event-ids
	query_handle = win32evtlog.EvtQuery(
		Path="Microsoft-Windows-WindowsUpdateClient/Operational",
		Flags=win32evtlog.EvtQueryReverseDirection | win32evtlog.EvtQueryChannelPath,
		Query="*[System/Provider[@Name='Microsoft-Windows-WindowsUpdateClient']]",
	)

	events = win32evtlog.EvtNext(query_handle, Count=10, Timeout=1)
	if not events:
		return False

	for event in events:
		xml = win32evtlog.EvtRender(event, win32evtlog.EvtRenderEventXml)
		logger.debug("Found WindowsUpdateClient event:", xml)
		dom = minidom.parseString(xml)
		elements = dom.getElementsByTagName("EventId")
		if not elements or not elements[0].firstChild or not elements[0].firstChild.nodeValue:
			continue

		event_id = int(elements[0].firstChild.nodeValue)
		# 43: Installation started
		# 44: Installation completed
		# 19: Installation successful
		# 20: Installation failed
		if event_id == 43:
			logger.info("Windows updates are running (event ID %d)", event_id)
			return True
		if event_id in (44, 19, 20):
			logger.info("Windows updates are not running (event ID %d)", event_id)
			return False

	return False
