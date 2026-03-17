# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import json
from unittest.mock import patch

import pytest

from opsi.opsiservice.server import get_opsiconfd_config
from opsi.opsiservice.server._common import _opsiconfd_get_config
from opsi.process import ProcessError


@pytest.mark.linux
def test_get_opsiconfd_config() -> None:
	with patch("opsi.opsiservice.server._common.OPSICONFD_GET_CONFIG_COMMAND", ["opsiconfd-command-not-found"]):
		assert get_opsiconfd_config() == {}
		_opsiconfd_get_config.cache_clear()

		with pytest.raises(ProcessError, match="No such file or directory"):
			get_opsiconfd_config(ignore_error=False)
		_opsiconfd_get_config.cache_clear()

	class Process:
		def get_stdout_text() -> str:
			return """{
				"websocket_protocol": "wsproto_opsiconfd",
				"websocket_open_timeout": 30,
				"log_slow_async_callbacks": 0.05,
				"addon_dirs": [
					"/usr/lib/opsiconfd/addons",
					"/var/lib/opsiconfd/addons"
				]
			}
			"""

	config = json.loads(Process.get_stdout_text())

	with patch("opsi.opsiservice.server._common.run_command", return_value=Process):
		assert get_opsiconfd_config() == config
		_opsiconfd_get_config.cache_clear()

		template = {
			"websocket_protocol": "",
			"websocket_open_timeout": 0,
			"log_level": 99,
		}
		res = get_opsiconfd_config(template=template)
		assert res["websocket_protocol"] == config["websocket_protocol"]
		assert res["websocket_open_timeout"] == config["websocket_open_timeout"]
		assert res["log_level"] == template["log_level"]
		assert "addon_dirs" not in res
		_opsiconfd_get_config.cache_clear()
