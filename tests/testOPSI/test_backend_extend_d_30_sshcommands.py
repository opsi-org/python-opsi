#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2017-2018 uib GmbH <info@uib.de>

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

		with mock.patch.object(backend._backend, '_getSSHCommandCustomFilename', return_value=filename):
			with mock.patch.object(backend._backend, '_getSSHCommandFilenames', return_value=[filename]):
				with mock.patch.object(backend._backend, '_isBuiltIn', return_value=False):
					yield


@contextmanager
def workWithBrokenCommandFile(backend):
	with workInTemporaryDirectory():
		element = {
			"id": "rechte_setzen",
			"menuText : Rechte setzen": "",  # <-- This is broken
			"commands": ["opsi-set-rights"],
			"position": 30,
			"needSudo": True,
			"tooltipText": "Rechte mittels opsi-set-rights setzen",
			"parentMenuText": "opsi"
		}

		filename = u'test_file.conf'

		with open(filename, "w") as f:
			json.dump(element, f)

		with mock.patch.object(backend._backend, '_getSSHCommandCustomFilename', return_value=filename):
			with mock.patch.object(backend._backend, '_getSSHCommandFilenames', return_value=[filename]):
				with mock.patch.object(backend._backend, '_isBuiltIn', return_value=False):
					yield


def getTestCommands():
	first = getTestCommand(u'utestmenu1', u'UTestMenu1', [u'test 1'], 5, True,  u'Test Tooltip1', u'Test Parent1')
	second = getTestCommand(u'utestmenu2', u'UTestMenu2', [u'test 2'], 52, True,  u'Test Tooltip2', u'Test Parent2')
	third = getTestCommand(u'utestmenu3', u'UTestMenu3', [u'test 3'], 53, True,  u'Test Tooltip3', u'Test Parent3')
	return first, second, third


def getTestCommand(commandId, menuText, commands, position, needSudo, tooltipText, parentMenuText):
	minimal = {
		u'menuText': menuText,
		u'commands': commands
	}
	full = {
		u'id': commandId,
		u'menuText': menuText,
		u'commands': commands,
		u'needSudo': needSudo,
		u'position': position,
		u'tooltipText': tooltipText,
		u'parentMenuText': parentMenuText
	}
	return CommandCollection(minimal, full)


def getTestOneCommand(mid, menuText, commands, position, needSudo, tooltipText, parentMenuText):
	commandcollection = getTestCommand(mid, menuText, commands, position, needSudo, tooltipText, parentMenuText)
	return commandcollection.full


def getTestCommandWithDefault(existingCommand):
	return {
		u'needSudo': False,
		u'position': 0,
		u'tooltipText': u'',
		u'parentMenuText': None,
		u'id': existingCommand["id"],
		u'menuText': existingCommand[u'menuText'],
		u'commands': existingCommand[u'commands'],
	}


def getSSHCommandCreationParameter():
	first, second, third = getTestCommands()
	return [
		[[first.minimal], [getTestCommandWithDefault(first.full)]],
		[[first.minimal, second.minimal], [getTestCommandWithDefault(first.full), getTestCommandWithDefault(second.full)]],
		[[first.minimal, second.minimal, third.minimal], [getTestCommandWithDefault(first.full), getTestCommandWithDefault(second.full), getTestCommandWithDefault(first.full)]],
	]


@pytest.mark.parametrize("val,expected_result", getSSHCommandCreationParameter())
def testSSHCommandCreations(backendManager, val, expected_result):
	with workWithEmptyCommandFile(backendManager):
		assert backendManager.SSHCommand_getObjects() == [], "first return of SSHCommand_getObjects should be an empty list"
		result = backendManager.SSHCommand_createObjects(val)
		compareLists(result, expected_result)


@pytest.mark.parametrize("val,expected_result", getSSHCommandCreationParameter())
def testSSHCommandCreation(backendManager, val, expected_result):
	with workWithEmptyCommandFile(backendManager):
		assert backendManager.SSHCommand_getObjects() == [], "first return of SSHCommand_getObjects should be an empty list"

		for command in val:
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
		commandFrom1 = next((item for item in list1 if item["menuText"] == dictcom["menuText"]), None)
		assert dictcom["menuText"] == commandFrom1["menuText"]
		assert dictcom["id"] == commandFrom1["id"]
		assert dictcom["commands"] == commandFrom1["commands"]
		assert dictcom["position"] == commandFrom1["position"]
		assert dictcom["needSudo"] == commandFrom1["needSudo"]
		assert dictcom["tooltipText"] == commandFrom1["tooltipText"]
		assert dictcom["parentMenuText"] == commandFrom1["parentMenuText"]


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
	with workWithEmptyCommandFile(backendManager):
		with pytest.raises(ValueError):
			if commandlist:
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
	with workWithEmptyCommandFile(backendManager):
		with pytest.raises(Exception):
			if commandlist:
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
	with workWithEmptyCommandFile(backendManager):
		yield backendManager


@pytest.fixture
def testCommands():
	return getTestCommands()


@pytest.fixture
def firstCommand(testCommands):
	return testCommands[0]


@pytest.fixture
def secondCommand(testCommands):
	return testCommands[1]


@pytest.fixture
def thirdCommand(testCommands):
	return testCommands[2]


def testGettingCommand(backendWithEmptyCommandFile, firstCommand):
	backend = backendWithEmptyCommandFile

	assert backend.SSHCommand_getObjects() == [], "first return of SSHCommand_getObjects should be an empty list"
	result = backend.SSHCommand_createObjects([firstCommand.minimal])

	commandWithDefaults = getTestCommandWithDefault(firstCommand.full)
	compareLists(result, [commandWithDefaults])


def testUpdatingSingleCommand(backendWithEmptyCommandFile, firstCommand):
	backend = backendWithEmptyCommandFile

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


def testUpdatingMultipleCommands(backendWithEmptyCommandFile, firstCommand, secondCommand, thirdCommand):
	backend = backendWithEmptyCommandFile

	com123_new_full = [
		modifySSHCommand(firstCommand.full, [u'MyNewTestCom1'], 11, True, u'MyNewTooltipText1', u'myParent1'),
		modifySSHCommand(secondCommand.full, [u'MyNewTestCom2'], 12, False, u'MyNewTooltipText2', u'myParent2'),
		modifySSHCommand(thirdCommand.full, [u'MyNewTestCom3'], 13, False, u'MyNewTooltipText3', u'myParent3')
	]

	assert backend.SSHCommand_getObjects() == [], "first return of SSHCommand_getObjects should be an empty list"
	backend.SSHCommand_createObjects([firstCommand.minimal, secondCommand.minimal])
	return_command = backend.SSHCommand_updateObjects(com123_new_full)
	compareLists(return_command, com123_new_full)


def testDeletingCommand(backendWithEmptyCommandFile, firstCommand, secondCommand):
	backend = backendWithEmptyCommandFile
	firstCommandWithDefaults = getTestCommandWithDefault(firstCommand.full)

	assert backend.SSHCommand_getObjects() == [], "first return of SSHCommand_getObjects should be an empty list"
	backend.SSHCommand_createObjects([firstCommand.minimal, secondCommand.minimal])
	compareLists(backend.SSHCommand_deleteObject(secondCommand.minimal["menuText"]), [firstCommandWithDefaults])


def testDeletingCommands(backendManager, firstCommand, secondCommand, thirdCommand):
	backend = backendManager
	thirdCommandWithDefaults = getTestCommandWithDefault(thirdCommand.full)

	with workWithEmptyCommandFile(backend):
		assert backend.SSHCommand_getObjects() == [], "first return of SSHCommand_getObjects should be an empty list"
		backend.SSHCommand_createObjects([firstCommand.minimal, secondCommand.minimal, thirdCommand.minimal])
		compareLists(backend.SSHCommand_deleteObjects([firstCommand.minimal["menuText"], secondCommand.minimal["menuText"], thirdCommand.minimal["menuText"]]), [])

	with workWithEmptyCommandFile(backend):
		assert backend.SSHCommand_getObjects() == [], "first return of SSHCommand_getObjects should be an empty list"
		backend.SSHCommand_createObjects([firstCommand.minimal, secondCommand.minimal, thirdCommand.minimal])
		compareLists(backend.SSHCommand_deleteObjects([firstCommand.minimal["menuText"], secondCommand.minimal["menuText"]]), [thirdCommandWithDefaults])
