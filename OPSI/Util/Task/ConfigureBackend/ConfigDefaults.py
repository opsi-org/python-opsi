# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2019 uib GmbH <info@uib.de>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
CLI Utility to change the config defaults.

.. versionadded:: 4.1.1.57

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from contextlib import contextmanager

from OPSI.Backend.BackendManager import BackendManager
from OPSI.Exceptions import BackendMissingDataError
from OPSI.Logger import LOG_NONE, Logger
from OPSI.Types import forceUnicodeList
from OPSI.UI import UIFactory

__all__ = ('editConfigDefaults', )

LOGGER = Logger()


def editConfigDefaults():
	bmconfig = dict(
		dispatchConfigFile=u'/etc/opsi/backendManager/dispatch.conf',
		backendConfigDir=u'/etc/opsi/backends',
		extensionConfigDir=u'/etc/opsi/backendManager/extend.d',
		depotbackend=False
	)

	with BackendManager(**bmconfig) as backend:
		configs = backend.config_getObjects()
		configs = [
			config for config in configs
			if not config.id.startswith(u'configed.saved_search.')
		]

		if not configs:
			raise BackendMissingDataError("Backend misses configurations!")

		maxConfigIdLen = max(len(config.id) for config in configs)
		entryFormat = u"%-10s %-" + str(maxConfigIdLen) + "s = %s"

		with disableConsoleLogging(), _getUI() as ui:
			while True:
				entries = []
				for config in configs:
					configType = '[unicode]'
					if config.getType() == 'BoolConfig':
						configType = '[bool]'

					values = u', '.join(forceUnicodeList(config.defaultValues))
					values = shortenStr(values, 60)
					entries.append(
						{
							"id": config.id,
							"name": entryFormat % (configType, config.id, values)
						}
					)

				selection = ui.getSelection(
					entries, radio=True,
					width=100, height=10,
					title=u'Please select config value to change',
					okLabel='Change', cancelLabel='Quit'
				)

				if not selection:
					return

				configId = None
				for entry in entries:
					if selection[0] == entry['name']:
						configId = entry['id']
						break

				selectedConfig = -1
				for index, config in enumerate(configs):
					if config.id == configId:
						selectedConfig = index
						break

				addNewValue = False
				cancelLabel = u'Back'
				title = u'Edit default values for: %s' % configs[selectedConfig].id
				text = configs[selectedConfig].description or u''
				if configs[selectedConfig].possibleValues:
					entries = []
					for possibleValue in configs[selectedConfig].possibleValues:
						entries.append({'name': possibleValue, 'value': possibleValue, 'selected': possibleValue in configs[selectedConfig].defaultValues})
					radio = not configs[selectedConfig].multiValue
					if configs[selectedConfig].editable:
						entries.append({'name': '<other value>', 'value': '<other value>', 'selected': False})
					selection = ui.getSelection(entries, radio=radio, width=65, height=10, title=title, text=text, cancelLabel=cancelLabel)

					if selection is None:
						continue
					if "<other value>" in selection:
						addNewValue = True
					else:
						configs[selectedConfig].setDefaultValues(selection)
				else:
					addNewValue = True

				if addNewValue:
					default = u''
					if configs[selectedConfig].defaultValues:
						default = configs[selectedConfig].defaultValues[0]
					value = ui.getValue(width=65, height=13, title=title, default=default, password=False, text=text, cancelLabel=cancelLabel)
					if value is None:
						continue

					possibleValues = configs[selectedConfig].getPossibleValues()
					if value not in possibleValues:
						possibleValues.append(value)
						configs[selectedConfig].setPossibleValues(possibleValues)
					configs[selectedConfig].setDefaultValues(value)

				backend.config_updateObjects([configs[selectedConfig]])


@contextmanager
def disableConsoleLogging():
	consoleLevel = LOGGER.getConsoleLevel()
	LOGGER.setConsoleLevel(LOG_NONE)
	try:
		yield
	finally:
		LOGGER.setConsoleLevel(consoleLevel)


@contextmanager
def _getUI():
	ui = UIFactory(type='snack')
	try:
		yield ui
	finally:
		ui.exit()


def shortenStr(string, length):
	if len(string) > length:
		return string[:length] + '...'

	return string
