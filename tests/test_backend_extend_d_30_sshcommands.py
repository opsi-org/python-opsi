#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2017 uib GmbH <info@uib.de>

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
Testing CRUD Methods for sshcommands (read from / write to jsonfile).

:author: Anna Sucher <a.sucher@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import json
import pytest
from contextlib import contextmanager
from collections import namedtuple

from .helpers import workInTemporaryDirectory, mock


CommandCollection = namedtuple("CommandCollection", "minimal full")


@contextmanager
def workWithEmptyCommandFile(backend):
	with workInTemporaryDirectory():
		filename = u'test_file.conf'
		with open(filename, "w"):
			pass
		with mock.patch.object(backend, '_getSSHCommandCustomFilename', return_value=filename):
			with mock.patch.object(backend, '_getSSHCommandFilenames', return_value=[filename]):
				with mock.patch.object(backend, '_isBuiltIn', return_value=False):
					yield


@contextmanager
def workWithBrokenCommandFile(backend):
	with workInTemporaryDirectory():
		filename = u'test_file.conf'
		element = {
			"id": "rechte_setzen",
			"menuText : Rechte setzen": "",  # <-- This is broken
			"commands": ["opsi-set-rights"],
			"position": 30,
			"needSudo": True,
			"tooltipText": "Rechte mittels opsi-set-rights setzen",
			"parentMenuText": "opsi"
		}

		with open(filename, "w") as f:
			json.dump(element, f)

		with mock.patch.object(backend._backend, '_getSSHCommandCustomFilename', return_value=filename):
			with mock.patch.object(backend._backend, '_getSSHCommandFilenames', return_value=[filename]):
				with mock.patch.object(backend._backend, '_isBuiltIn', return_value=False):
					yield backend


def getTestCommands():
	(com1, com1_full) = getTestCommand(u'utestmenu1', u'UTestMenu1', [u'test 1'], 5, True,  u'Test Tooltip1', u'Test Parent1')
	(com2, com2_full) = getTestCommand(u'utestmenu2', u'UTestMenu2', [u'test 2'], 52, True,  u'Test Tooltip2', u'Test Parent2')
	(com3, com3_full) = getTestCommand(u'utestmenu3', u'UTestMenu3', [u'test 3'], 53, True,  u'Test Tooltip3', u'Test Parent3')
	return CommandCollection(com1, com1_full), CommandCollection(com2, com2_full), CommandCollection(com3, com3_full)


def getTestCommand(commandId, menuText, commands, position, needSudo, tooltipText, parentMenuText):
	this = {
		u'menuText': menuText,
		u'commands': commands
	}
	thisfull = {
		u'id': commandId,
		u'menuText': menuText,
		u'commands': commands,
		u'needSudo': needSudo,
		u'position': position,
		u'tooltipText': tooltipText,
		u'parentMenuText': parentMenuText
	}
	return (this, thisfull)


def getTestOneCommand(mid, menuText, commands, position, needSudo, tooltipText, parentMenuText):
	(_, thisfull) = getTestCommand(mid, menuText, commands, position, needSudo, tooltipText, parentMenuText)
	return thisfull


def getTestCommandWithDefault(existingCommand):
	com = {
		u'needSudo': False,
		u'position': 0,
		u'tooltipText': u'',
		u'parentMenuText': None
	}

	com[u'id'] = existingCommand["id"]
	com[u'menuText'] = existingCommand[u'menuText']
	com[u'commands'] = existingCommand[u'commands']
	return com


def getSSHCommandCreationParameter():
	(com1_min, com1_full), (com2_min, com2_full), (com3_min, com3_full) = getTestCommands()
	return [
		[[com1_min], [getTestCommandWithDefault(com1_full)]],
		[[com1_min, com2_min], [getTestCommandWithDefault(com1_full), getTestCommandWithDefault(com2_full)]],
		[[com1_min, com2_min, com3_min], [getTestCommandWithDefault(com1_full), getTestCommandWithDefault(com2_full), getTestCommandWithDefault(com1_full)]],
	]


@pytest.mark.parametrize("val,expected_result", getSSHCommandCreationParameter())
def testSSHCommandCreations(backendManager, val, expected_result):
	with workWithEmptyCommandFile(backendManager._backend):
		assert backendManager.SSHCommand_getObjects() == [], "first return of SSHCommand_getObjects should be an empty list"
		result = backendManager.SSHCommand_createObjects(val)
		compareLists(result, expected_result)


@pytest.mark.parametrize("val,expected_result", getSSHCommandCreationParameter())
def testSSHCommandCreation(backendManager, val, expected_result):
	with workWithEmptyCommandFile(backendManager._backend):
		assert backendManager.SSHCommand_getObjects() == [], "first return of SSHCommand_getObjects should be an empty list"
		for x in range(0, len(val)):
			command = val[x]
			result = backendManager.SSHCommand_createObject(
				command.get("menuText"),
				command.get("commands"),
				command.get("position"),
				command.get("needSudo"),
				command.get("tooltipText"),
				command.get("parentMenuText")
			)
		compareLists(result, expected_result)


def compareLists(list1, list2):
	assert len(list1) == len(list2)
	for dictcom in list2:
		assert dictcom in list1
	for dictcom in list2:
		my_item = next((item for item in list1 if item["menuText"] == dictcom["menuText"]), None)
		assert dictcom["menuText"] == my_item["menuText"]
		assert dictcom["id"] == my_item["id"]
		assert dictcom["commands"] == my_item["commands"]
		assert dictcom["position"] == my_item["position"]
		assert dictcom["needSudo"] == my_item["needSudo"]
		assert dictcom["tooltipText"] == my_item["tooltipText"]
		assert dictcom["parentMenuText"] == my_item["parentMenuText"]


def getSSHCommandCreationExceptionsParameter():
	return [
		[getTestOneCommand(None, None, None, 10, True, u'', None)],
		[getTestOneCommand(None, u'TestMenuText1', {}, 10, True, u'', None)],
		[getTestOneCommand(None, u'TestMenuText2', [], u'', True, u'', None)],
		[getTestOneCommand(None, u'TestMenuText3', [], u'10', u'True', u'', None)],
		[getTestOneCommand(None, u'TestMenuText4', [u'foo'], 10, u'True', u'', None)],
		[getTestOneCommand(None, u'TestMenuText5', [u'foo'], 10, u'True', u'', None)]
	]


@pytest.mark.parametrize("commandlist", getSSHCommandCreationExceptionsParameter())
def testSSHCommandCreationExceptions(backendManager,  commandlist):
	with workWithEmptyCommandFile(backendManager._backend):
		with pytest.raises(Exception):
			if len(commandlist) <= 1:
				command = commandlist[0]
				backendManager.SSHCommand_createObject(
					command.get("menuText"),
					command.get("commands"),
					command.get("position"),
					command.get("needSudo"),
					command.get("tooltipText"),
					command.get("parentMenuText")
				)
			backendManager.SSHCommand_createObjects(commandlist)


def getSSHCommandUpdateExceptionsParameter():
	return [
		[getTestOneCommand(None, None, None, 10, True, u'', None)],
		[getTestOneCommand(None, u'TestMenuText1', {}, 10, True, u'', None)],
		[getTestOneCommand(None, u'TestMenuText2', [], u'10', u'True', u'', None)],
		[getTestOneCommand(None, u'TestMenuText3', [u'foo'], 10, u'True', u'', None)]
	]


@pytest.mark.parametrize("commandlist", getSSHCommandCreationExceptionsParameter())
def testSSHCommandUpdateExceptions(backendManager,  commandlist):
	with workWithEmptyCommandFile(backendManager._backend):
		with pytest.raises(Exception):
			if len(commandlist) <= 1:
				command = commandlist[0]
				backendManager.SSHCommand_updateObject(
					command.get("menuText", None),
					command.get("commands", None),
					command.get("position", None),
					command.get("needSudo", None),
					command.get("tooltipText", None),
					command.get("parentMenuText", None)
				)
			backendManager.SSHCommand_updateObjects(commandlist)


@pytest.fixture
def backendWithBrokenCommandFile(backendManager):
	with workWithBrokenCommandFile(backendManager) as backend:
		yield backend


def testBrokenCommandFileRaisesException(backendWithBrokenCommandFile):
	with pytest.raises(Exception):
		backendWithBrokenCommandFile.SSHCommand_deleteObjects()


def modifySSHCommand(command, commandList, position, needsSudo, tooltipText, parentMenuText):
	command["commands"] = commandList
	command["position"] = position
	command["needSudo"] = needsSudo
	command["tooltipText"] = tooltipText
	command["parentMenuText"] = parentMenuText
	return command


@pytest.fixture
def backendWithEmptyCommandFile(backendManager):
	with workWithEmptyCommandFile(backendManager._backend):
		yield backendManager


def testGettingCommand(backendWithEmptyCommandFile):
	backend = backendWithEmptyCommandFile

	commands = getTestCommands()
	firstCommand = commands[0]

	assert backend.SSHCommand_getObjects() == [], "first return of SSHCommand_getObjects should be an empty list"
	result = backend.SSHCommand_createObjects([firstCommand.minimal])

	commandWithDefaults = getTestCommandWithDefault(firstCommand.full)
	compareLists(result, [commandWithDefaults])


def testUpdatingSingleCommand(backendWithEmptyCommandFile):
	backend = backendWithEmptyCommandFile

	commands = getTestCommands()
	firstCommand = commands[0]

	assert backend.SSHCommand_getObjects() == [], "first return of SSHCommand_getObjects should be an empty list"
	backend.SSHCommand_createObject(firstCommand.full["menuText"], firstCommand.full["commands"])
	com1_new_full = firstCommand.full
	com1_new_full = modifySSHCommand(com1_new_full, [u'MyNewTestCom'], 10, True, u'MyNewTooltipText', u'myParent')
	return_command = backend.SSHCommand_updateObject(
		firstCommand.full["menuText"],
		com1_new_full["commands"],
		com1_new_full["position"],
		com1_new_full["needSudo"],
		com1_new_full["tooltipText"],
		com1_new_full["parentMenuText"]
	)

	compareLists(return_command, [com1_new_full])


def testUpdatingMultipleCommands(backendWithEmptyCommandFile):
	backend = backendWithEmptyCommandFile

	firstCommand, secondCommand, thirdCommand = getTestCommands()

	com123_new_full = [firstCommand.full, secondCommand.full, thirdCommand.full]
	com123_new_full[0] = modifySSHCommand(com123_new_full[0], [u'MyNewTestCom1'], 11, True, u'MyNewTooltipText1', u'myParent1')
	com123_new_full[1] = modifySSHCommand(com123_new_full[1], [u'MyNewTestCom2'], 12, False, u'MyNewTooltipText2', u'myParent2')
	com123_new_full[2] = modifySSHCommand(com123_new_full[2], [u'MyNewTestCom3'], 13, False, u'MyNewTooltipText3', u'myParent3')
	assert backend.SSHCommand_getObjects() == [], "first return of SSHCommand_getObjects should be an empty list"
	backend.SSHCommand_createObjects([firstCommand.minimal, secondCommand.minimal])
	return_command = backend.SSHCommand_updateObjects(com123_new_full)
	compareLists(return_command, com123_new_full)


def testDeletingCommand(backendWithEmptyCommandFile):
	backend = backendWithEmptyCommandFile

	commands = getTestCommands()
	firstCommand = commands[0]
	secondCommand = commands[1]

	firstCommandWithDefaults = getTestCommandWithDefault(firstCommand.full)

	assert backend.SSHCommand_getObjects() == [], "first return of SSHCommand_getObjects should be an empty list"
	backend.SSHCommand_createObjects([firstCommand.minimal, secondCommand.minimal])
	compareLists(backend.SSHCommand_deleteObject(secondCommand.minimal["menuText"]), [firstCommandWithDefaults])


def testDeletingCommands(backendManager):
	backend = backendManager

	firstCommand, secondCommand, thirdCommand = getTestCommands()
	thirdCommandWithDefaults = getTestCommandWithDefault(thirdCommand.full)

	with workWithEmptyCommandFile(backend._backend):
		assert backend.SSHCommand_getObjects() == [], "first return of SSHCommand_getObjects should be an empty list"
		backend.SSHCommand_createObjects([firstCommand.minimal, secondCommand.minimal, thirdCommand.minimal])
		compareLists(backend.SSHCommand_deleteObjects([firstCommand.minimal["menuText"], secondCommand.minimal["menuText"], thirdCommand.minimal["menuText"]]), [])

	with workWithEmptyCommandFile(backend._backend):
		assert backend.SSHCommand_getObjects() == [], "first return of SSHCommand_getObjects should be an empty list"
		backend.SSHCommand_createObjects([firstCommand.minimal, secondCommand.minimal, thirdCommand.minimal])
		compareLists(backend.SSHCommand_deleteObjects([firstCommand.minimal["menuText"], secondCommand.minimal["menuText"]]), [thirdCommandWithDefaults])
