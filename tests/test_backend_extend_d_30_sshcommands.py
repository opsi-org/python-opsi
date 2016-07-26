#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2015 uib GmbH <info@uib.de>

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
from .Backends.File import FileBackendBackendManagerMixin
from .helpers import workInTemporaryDirectory, mock
import unittest, pytest, json
from contextlib import contextmanager

@contextmanager
def workWithEmptyCommandFile(backend):
	with workInTemporaryDirectory():
		filename = u'test_file.conf'
		with open(filename, "w"):
			pass
		with mock.patch.object(backend, '_getSSHCommandCustomFilename', return_value=filename):
			with mock.patch.object(backend, '_getSSHCommandFilenames', return_value=[filename]):
				with mock.patch.object(backend, '_isBuildIn', return_value=False):
					yield

@contextmanager
def workWithBrokenCommandFile(backend):
	 import json
	 with workInTemporaryDirectory():
	 	filename = u'test_file.conf'
		element = {"id":"rechte_setzen", "menuText : Rechte setzen":"", "commands":["opsi-set-rights"], "position":30,"needSudo":True, "tooltipText":"Rechte mittels opsi-set-rights setzen", "parentMenuText":"opsi"}
		with open(filename, "w") as f:
			json.dump(element, f)
		with mock.patch.object(backend, '_getSSHCommandCustomFilename', return_value=filename):
			with mock.patch.object(backend, '_getSSHCommandFilenames', return_value=[filename]):
				with mock.patch.object(backend, '_isBuildIn', return_value=False):
					yield

def getTestCommands():
	(com1, com1_full) = getTestCommand(u'utestmenu1', u'UTestMenu1', [u'test 1'], 5, True,  u'Test Tooltip1', u'Test Parent1' )
	(com2, com2_full) = getTestCommand(u'utestmenu2', u'UTestMenu2', [u'test 2'], 52, True,  u'Test Tooltip2', u'Test Parent2' )
	(com3, com3_full) = getTestCommand(u'utestmenu3', u'UTestMenu3', [u'test 3'], 53, True,  u'Test Tooltip3', u'Test Parent3' )
	return (com1, com1_full), (com2, com2_full), (com3, com3_full)

def getTestCommand( mid, menuText, commands, position, needSudo, tooltipText, parentMenuText):
	thisid=mid
	thismenuText=menuText
	thiscommands=commands
	thisposition=position
	thisneedSudo=needSudo
	thistooltipText=tooltipText
	thisparentMenuText=parentMenuText
	this={u'menuText':thismenuText, u'commands':thiscommands}
	thisfull={u'id':thisid, u'menuText':thismenuText, u'commands':thiscommands, u'needSudo':thisneedSudo, u'position':thisposition, u'tooltipText':thistooltipText, u'parentMenuText':thisparentMenuText}
	return  (this, thisfull)

def getTestOneCommand( mid, menuText, commands, position, needSudo, tooltipText, parentMenuText):
	(this, thisfull) = getTestCommand( mid, menuText, commands, position, needSudo, tooltipText, parentMenuText)
	return thisfull

def getTestCommandWithDefault( existingcom):
	def getDefaults():
		def_position=0
		def_needSudo=False
		def_tooltipText=u''
		def_parentMenuText=None
		return {u'needSudo':def_needSudo, u'position':def_position, u'tooltipText':def_tooltipText, u'parentMenuText':def_parentMenuText}
	com = getDefaults()
	com[u'id'] = existingcom["id"]
	com[u'menuText'] = existingcom[u'menuText']
	com[u'commands'] = existingcom[u'commands']
	return com

def getSSHCommandCreationParameter():
	(com1_min, com1_full), (com2_min, com2_full), (com3_min, com3_full) = getTestCommands()
	# c1 = getTestOneCommand( None,"menuText1", [u'commands'], 10, True, u'testtooltiptext', u'testparentmenu')
	# c1_f = c1
	# c1_f["id"] = "menutext1"
	#  # = getTestOneCommand( "menutext1","menuText1", [u'commands'], 10, True, u'testtooltiptext', u'testparentmenu')
	# c2 = getTestOneCommand( None,"menuText2", [u'commands'], 10, False, u'', u'testparentmenu')
	# c2_f = c2
	# c2_f["id"] = "menutext2"
	# # c2_f = getTestOneCommand( "menutext2","menuText2", [u'commands'], 10, False, u'', u'testparentmenu')

	# c3 = getTestOneCommand( None,"menuText2", [u'commands'], 10, False, False, False)
	# c3_f = c3
	# c3_f["id"] = "menutext3"
	# # c3_f = getTestOneCommand( "menutext3","menuText2", [u'commands'], 10, False, False, False)

	# c4 = getTestOneCommand( None,"menuText2", [u'commands'], 10, False, False, None)
	# c4_f = c4
	# c4_f["id"] = "menutext4"
	# # c4_f = getTestOneCommand( "menutext4","menuText2", [u'commands'], 10, False, False, None)

	# c5 = getTestOneCommand( None,"menuText2", [u'commands'], 10, False, 50, 20)
	# c5_f = c5
	# c5_f["id"] = "menutext5"
	# # c5_f = getTestOneCommand( "menutext5","menuText2", [u'commands'], 10, False, 50, 20)

	# c6 = getTestOneCommand( None,"menuText2", [u'commands'], 10, False, u'', False)
	# c6_f = c6
	# c6_f["id"] = "menutext6"
	# # c6_f = getTestOneCommand( "menutext6","menuText2", [u'commands'], 10, False, u'', False)

	# c7 = getTestOneCommand( None,"menuText2", ["commands"], 10, False, u'', u'')
	# c7_f = c7
	# c7_f["id"] = "menutext7"
	# # c7_f = getTestOneCommand( "menutext7","menuText2", ["commands"], 10, False, u'', u'')
	return [
		[[com1_min] , [getTestCommandWithDefault(com1_full)]],
		[[com1_min, com2_min] , [getTestCommandWithDefault(com1_full), getTestCommandWithDefault(com2_full)]],
		[[com1_min, com2_min, com3_min] , [getTestCommandWithDefault(com1_full), getTestCommandWithDefault(com2_full), getTestCommandWithDefault(com1_full)]],
		# [[c1] , [c1_f]],
		# [[c2] , [c2_f]],
		# [[c3] , [c3_f]],
		# [[c4] , [c4_f]],
		# [[c5] , [c5_f]],
		# [[c6] , [c6_f]],
		# [[c7] , [c7_f]]
		# [[c1,c2] , [c1_f,c2_f]]
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
			result = backendManager.SSHCommand_createObject(command.get("menuText"), command.get("commands"),command.get("position"), command.get("needSudo"), command.get("tooltipText"), command.get("parentMenuText"))
		compareLists(result, expected_result)

def compareLists(list1, list2):
	print(list1)
	print(list2)
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
		[getTestOneCommand( None, None, None, 10, True, u'', None)],
		[getTestOneCommand( None, u'TestMenuText1', {}, 10, True, u'', None)],
		[getTestOneCommand( None, u'TestMenuText2', [], u'', True, u'', None)],
		[getTestOneCommand( None, u'TestMenuText3', [], u'10', u'True', u'', None)],
		[getTestOneCommand( None, u'TestMenuText4', [u'foo'], 10, u'True', u'', None)],
		[getTestOneCommand( None, u'TestMenuText5', [u'foo'], 10, u'True', u'', None)]
		# [ getTestOneCommand( None, u'TestMenuText4', [u'foo'], 10, True, u'', None)].append(getTestOneCommand( None, u'TestMenuText4', [u'foo'], 10, True, u'', None))
		# [getTestOneCommand( None, u'TestMenuText6', [u'foo'], 10, True, u'', None)]
	]
@pytest.mark.parametrize("commandlist", getSSHCommandCreationExceptionsParameter())
def testSSHCommandCreationExceptions(backendManager,  commandlist):
	with workWithEmptyCommandFile(backendManager._backend):
		with pytest.raises(Exception):
			if len(commandlist) <= 1:
				command = commandlist[0]
				backendManager.SSHCommand_createObject(command.get("menuText"), command.get("commands"),command.get("position"), command.get("needSudo"), command.get("tooltipText"), command.get("parentMenuText"))
			backendManager.SSHCommand_createObjects(commandlist)


def getSSHCommandUpdateExceptionsParameter():
	return [
		[ getTestOneCommand( None, None, None, 10, True, u'', None)],
		[ getTestOneCommand( None, u'TestMenuText1', {}, 10, True, u'', None)],
		[ getTestOneCommand( None, u'TestMenuText2', [], u'10', u'True', u'', None)],
		[ getTestOneCommand( None, u'TestMenuText3', [u'foo'], 10, u'True', u'', None)]
	]
@pytest.mark.parametrize("commandlist", getSSHCommandCreationExceptionsParameter())
def testSSHCommandUpdateExceptions(backendManager,  commandlist):
	with workWithEmptyCommandFile(backendManager._backend):
		with pytest.raises(Exception):
			if len(commandlist) <= 1:
				command = commandlist[0]
				backendManager.SSHCommand_updateObject(command.get("menuText", None), command.get("commands", None),command.get("position", None), command.get("needSudo", None), command.get("tooltipText", None), command.get("parentMenuText", None))
			backendManager.SSHCommand_updateObjects(commandlist)


class SSHCommandsTestCase(unittest.TestCase, FileBackendBackendManagerMixin):

	"""
	Testing the crud methods for json commands .
	"""
	def setUp(self):
		self.maxDiff = None
		self.setUpBackend()
		
		(self.com1_min, self.com1_full), (self.com2_min, self.com2_full), (self.com3_min, self.com3_full) = getTestCommands()
		self.com1_withDefaults = getTestCommandWithDefault(self.com1_full)
		self.com2_withDefaults = getTestCommandWithDefault(self.com2_full)
		self.com3_withDefaults = getTestCommandWithDefault(self.com3_full)
		(self.com_withFailures_min, self.com_withFailures) = getTestCommand(u'utestmenu1', 20, u'test 1', u'O', u'Nein', False, False)


	def tearDown(self):
		self.tearDownBackend()


	def testExceptionGetCommand(self):
		with workWithBrokenCommandFile(self.backend._backend):
			self.assertRaises(Exception, self.backend.SSHCommand_deleteObjects)

	def testGetCommand(self):
		with workWithEmptyCommandFile(self.backend._backend):
			self.assertEqual(self.backend.SSHCommand_getObjects(), [], "first return of SSHCommand_getObjects should be an empty list")
			result = self.backend.SSHCommand_createObjects([self.com1_min])
			compareLists(result, [self.com1_withDefaults])
			# self.assertListEqual(self.backend.SSHCommand_getObjects(), self.commandlist_com1_withdefval_full)

	# def testCreateCommands(self):
	# 	with workWithEmptyCommandFile(self.backend._backend):
	# 		self.assertEqual(self.backend.SSHCommand_getObjects(), [], "first return of SSHCommand_getObjects should be an empty list")
	# 		self.createObjects([self.com1_min, self.com2_min], [self.com1_withDefaults, self.com2_withDefaults])
	
	# def createObjects(self, val, expected_result):
	# 	result = self.backend.SSHCommand_createObjects(val)
	# 	assert len(result) == len(result)
	# 	for dictcom in expected_result:
	# 		assert dictcom in result

	# def testCreateCommand(self):
	# 	with workWithEmptyCommandFile(self.backend._backend):
	# 		self.assertEqual(self.backend.SSHCommand_getObjects(), [], "first return of SSHCommand_getObjects should be an empty list")
	# 		return_value = self.backend.SSHCommand_createObject( self.com1["menuText"], self.com1["commands"])
	# 		self.assertListEqual(return_value, self.commandlist_com1_withdefval_full)
	# 	with workWithEmptyCommandFile(self.backend._backend):
	# 		self.assertEqual(self.backend.SSHCommand_getObjects(), [], "first return of SSHCommand_getObjects should be an empty list")
	# 		return_value = self.backend.SSHCommand_createObject( self.com1["menuText"], self.com1_string)
	# 		self.assertListEqual(return_value, self.commandlist_com1_withdefval_full)
			

	# def testCreateCommands1(self):
	# 	with workWithEmptyCommandFile(self.backend._backend):
	# 		self.assertEqual(self.backend.SSHCommand_getObjects(), [], "first return of SSHCommand_getObjects should be an empty list")
	# 		self.assertListEqual(self.backend.SSHCommand_createObjects( self.commandlist_com1), self.commandlist_com1_withdefval_full)
	# 		# self.assertListEqual(self.backend.SSHCommand_createObjects( self.commandlist_com12), self.commandlist_com12_withdefval_full)

	# 		# print ('1:' + self.commandlist_com12)
	# 		# print ('2:' + self.commandlist_com12_withdefval_full)
	# def testCreateCommands3(self):
	# 	with workWithEmptyCommandFile(self.backend._backend):
	# 		self.assertEqual(self.backend.SSHCommand_getObjects(), [], "first return of SSHCommand_getObjects should be an empty list")
	# 		self.assertListEqual(self.backend.SSHCommand_createObjects( self.commandlist_com123), self.commandlist_com123_withdefval_full)
	def setNewSSHCommand(self, c, com, p, ns, ttt, pmt):
		c["commands"]=com
		c["position"]=p
		c["needSudo"]=ns
		c["tooltipText"]=ttt
		c["parentMenuText"]=pmt
		return c


	def testUpdateCommand(self):
		with workWithEmptyCommandFile(self.backend._backend):
			self.assertEqual(self.backend.SSHCommand_getObjects(), [], "first return of SSHCommand_getObjects should be an empty list")
			self.backend.SSHCommand_createObject( self.com1_full["menuText"], self.com1_full["commands"])
			com1_new_full = self.com1_full
			com1_new_full = self.setNewSSHCommand(com1_new_full, [u'MyNewTestCom'], 10, True, u'MyNewTooltipText', u'myParent')
			print(com1_new_full)
			return_command = self.backend.SSHCommand_updateObject( self.com1_full["menuText"], com1_new_full["commands"], com1_new_full["position"], com1_new_full["needSudo"], com1_new_full["tooltipText"], com1_new_full["parentMenuText"])
			compareLists(return_command, [com1_new_full])
			# compareLists(return_command, [self.com1_full, self.com2_full, self.com3_full])

	def testUpdateCommands(self):
		with workWithEmptyCommandFile(self.backend._backend):
			com123_new_full = [self.com1_full, self.com2_full, self.com3_full]
			com123_new_full[0] = self.setNewSSHCommand(com123_new_full[0], [u'MyNewTestCom1'], 11, True, u'MyNewTooltipText1', u'myParent1')
			com123_new_full[1] = self.setNewSSHCommand(com123_new_full[1], [u'MyNewTestCom2'], 12, False, u'MyNewTooltipText2', u'myParent2')
			com123_new_full[2] = self.setNewSSHCommand(com123_new_full[2], [u'MyNewTestCom3'], 13, False, u'MyNewTooltipText3', u'myParent3')
			self.assertEqual(self.backend.SSHCommand_getObjects(), [], "first return of SSHCommand_getObjects should be an empty list")
			self.backend.SSHCommand_createObjects( [self.com1_min, self.com2_min])
			return_command = self.backend.SSHCommand_updateObjects( com123_new_full)
			compareLists(return_command, com123_new_full)


	def testDeleteCommand(self):
		with workWithEmptyCommandFile(self.backend._backend):
			self.assertEqual(self.backend.SSHCommand_getObjects(), [], "first return of SSHCommand_getObjects should be an empty list")
			self.backend.SSHCommand_createObjects([self.com1_min, self.com2_min])
			compareLists(self.backend.SSHCommand_deleteObject(self.com2_min["menuText"]), [self.com1_withDefaults])
			# self.assertListEqual(self.backend.SSHCommand_deleteObject(self.com2_min["menuText"]), [self.com1_withDefaults])

	def testDeleteCommands(self):
		with workWithEmptyCommandFile(self.backend._backend):
			self.assertEqual(self.backend.SSHCommand_getObjects(), [], "first return of SSHCommand_getObjects should be an empty list")
			self.backend.SSHCommand_createObjects([self.com1_min, self.com2_min, self.com3_min])
			compareLists(self.backend.SSHCommand_deleteObjects( [self.com1_min["menuText"], self.com2_min["menuText"], self.com3_min["menuText"]]), [])
			# self.assertListEqual(self.backend.SSHCommand_deleteObjects( [self.com1_min["menuText"], self.com2_min["menuText"], self.com3_min["menuText"]]), [])
		with workWithEmptyCommandFile(self.backend._backend):
			self.assertEqual(self.backend.SSHCommand_getObjects(), [], "first return of SSHCommand_getObjects should be an empty list")
			self.backend.SSHCommand_createObjects([self.com1_min, self.com2_min, self.com3_min])
			compareLists(self.backend.SSHCommand_deleteObjects([self.com1_min["menuText"], self.com2_min["menuText"]]), [self.com3_withDefaults])
			# self.assertListEqual(self.backend.SSHCommand_deleteObjects([self.com1_min["menuText"], self.com2_min["menuText"]]), [self.com3_withDefaults])

	# def testExceptionsCreateObject1(self):
	# 	with workWithEmptyCommandFile(self.backend._backend):
	# 		self.assertRaises(Exception, self.backend.SSHCommand_createObject, None, None)
	# 		# self.assertRaises(Exception, self.backend.SSHCommand_createObject, self.com1_menuText, self.failure_com1_commands)
	# def testExceptionsCreateObject2(self):
	# 	with workWithEmptyCommandFile(self.backend._backend):
	# 		self.assertRaises(Exception, self.backend.SSHCommand_createObject, self.com1_full["menuText"], self.com1_full["commands"], self.com_withFailures["position"])
	# def testExceptionsCreateObject3(self):
	# 	with workWithEmptyCommandFile(self.backend._backend):
	# 		self.assertRaises(ValueError, self.backend.SSHCommand_createObject, self.com1_menuText, self.com1_commands, self.com1_position, self.failure_com1_needSudo)
	# def testExceptionsCreateObject4(self):
	# 	with workWithEmptyCommandFile(self.backend._backend):
	# 		self.assertRaises(Exception, self.backend.SSHCommand_createObject, self.com1_menuText, self.com1_commands, self.com1_position, self.com1_needSudo, self.failure_com1_tooltipText)
	# def testExceptionsCreateObject5(self):
	# 	with workWithEmptyCommandFile(self.backend._backend):
	# 		self.assertRaises(Exception, self.backend.SSHCommand_createObject, self.com1_menuText, self.com1_commands, self.com1_position, self.com1_needSudo, self.com1_tooltipText, self.failure_com1_parentMenuText)
	# def testExceptionsCreateObject6(self):
	# 	with workWithEmptyCommandFile(self.backend._backend):
	# 		self.assertListEqual(self.backend.SSHCommand_createObjects( self.commandlist_com1), self.commandlist_com1_withdefval_full)
	# def testExceptionsCreateObject7(self):
	# 	with workWithEmptyCommandFile(self.backend._backend):
	# 		self.assertRaises(Exception, self.backend.SSHCommand_createObject, self.com1_menuText, self.com1_commands, self.com1_position, self.com1_needSudo, self.com1_tooltipText, self.com1_parentMenuText)

	# def testExceptionsCreateObjects(self):
	# 	with workWithEmptyCommandFile(self.backend._backend):
	# 		self.assertRaises(Exception, self.backend.SSHCommand_createObjects, u'[this, is, not, a list]')
	# 		self.assertRaises(Exception, self.backend.SSHCommand_createObjects, [u'{this:is}', u'{not a : dictionary}'])
	# def testExceptionsCreateObjects1(self):
	# 	failure_com1_noMenuText=[{u'FailureMenuText':self.com1_min["menuText"], u'commands':self.com_withFailures["commands"]}]
	# 	with workWithEmptyCommandFile(self.backend._backend):
	# 		self.assertRaises(Exception, self.backend.SSHCommand_createObjects, failure_com1_noMenuText)
	# def testExceptionsCreateObjects2(self):
	# 	self.failure_com1_menuTextFalseType=[{u'menuText':self.failure_com1_menuText, u'commands':self.failure_com1_commands}]
	# 	with workWithEmptyCommandFile(self.backend._backend):
	# 		self.assertRaises(Exception, self.backend.SSHCommand_createObjects, self.failure_com1_menuTextFalseType)
			
	# def testExceptionsCreateObjects3(self):
	# 	self.failure_com1_noCommands=[{u'menuText':self.com1_menuText, u'falseCommands':self.com1_commands}]
	# 	with workWithEmptyCommandFile(self.backend._backend):
	# 		self.assertRaises(Exception, self.backend.SSHCommand_createObjects, self.failure_com1_noCommands)

	# def testExceptionsCreateObjects4(self):
		# with workWithEmptyCommandFile(self.backend._backend):
	# def testExceptionsCreateObjects4(self):
	# 	self.failure_com1_commandsFalseType=[{u'menuText':self.com1_menuText, u'commands':self.failure_com1_commands}]
	# 	with workWithEmptyCommandFile(self.backend._backend):
	# 		# self.assertRaises(Exception, self.backend.SSHCommand_createObjects, [])
	# 		# self.assertRaises(Exception, self.backend.SSHCommand_createObjects, self.failure_com1_commandsFalseType)
	# 		self.assertRaises(Exception, self.backend.SSHCommand_createObjects, self.commandlist_com11)

	# def testForceCommands(self):
		# with workWithEmptyCommandFile(self.backend._backend):
			# self. 
		


	# def testExceptionsUpdateObject(self):
	# 	with workWithEmptyCommandFile(self.backend._backend):
	# 		self.assertRaises(Exception, self.backend.SSHCommand_updateObject, None, None)
	# def testExceptionsUpdateObject1(self):
	# 	with workWithEmptyCommandFile(self.backend._backend):
	# 		self.assertRaises(Exception, self.backend.SSHCommand_updateObject, self.com1_menuText, self.failure_com1_commands)
	# def testExceptionsUpdateObject2(self):
	# 	with workWithEmptyCommandFile(self.backend._backend):
	# 		self.assertRaises(Exception, self.backend.SSHCommand_updateObject, self.com1_menuText, self.com1_commands, self.failure_com1_position)
	# def testExceptionsUpdateObject3(self):
	# 	with workWithEmptyCommandFile(self.backend._backend):
	# 		self.assertRaises(Exception, self.backend.SSHCommand_updateObject, self.com1_menuText, self.com1_commands, self.com1_position, self.failure_com1_needSudo)
	# def testExceptionsUpdateObject4(self):
	# 	with workWithEmptyCommandFile(self.backend._backend):
	# 		self.assertRaises(Exception, self.backend.SSHCommand_updateObject, self.com1_menuText, self.com1_commands, self.com1_position, self.com1_needSudo, self.failure_com1_tooltipText)
	# def testExceptionsUpdateObject5(self):
	# 	with workWithEmptyCommandFile(self.backend._backend):
	# 		self.assertRaises(Exception, self.backend.SSHCommand_updateObject, self.com1_menuText, self.com1_commands, self.com1_position, self.com1_needSudo, self.com1_tooltipText, self.failure_com1_parentMenuText)
	# 		#self.assertListEqual(self.backend.SSHCommand_createObjects( self.commandlist_com1), self.commandlist_com1_withdefval_full)
	# 		#self.assertRaises(Exception, self.backend.SSHCommand_updateObject, self.com1_menuText, self.com1_commands, self.com1_position, self.com1_needSudo, self.com1_tooltipText, self.com1_parentMenuText)

	# def testExceptionsKeysUpdateObjects(self):
	# 	with workWithEmptyCommandFile(self.backend._backend):
	# 		self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, u'[this, is, not, a list]')
	# 		self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, None)
	# 		self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, [])
	# 		self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, [u'{this:is}', u'{not a : dictionary}'])
	# def testExceptionsKeysUpdateObjects1(self):
	# 	# with workWithEmptyCommandFile(self.backend._backend):
	# # def testExceptionsKeysUpdateObjects2(self):
	# 	self.failure_com1_noMenuText=[{u'FailureMenuText':self.com1_menuText, u'commands':self.failure_com1_commands}]
	# 	self.failure_com1_noCommands=[{u'menuText':self.com1_menuText, u'falseCommands':self.com1_commands}]
	# 	self.failure_com1_noPosition=[{u'menuText':self.com1_menuText, u'commands':self.failure_com1_commands, u'falsePosition':10}]
	# 	self.failure_com1_noNeedSudo=[{u'menuText':self.com1_menuText, u'commands':self.failure_com1_commands, u'position':10, u'FalseNeedSudo':False}]
	# 	self.failure_com1_noTooltipText=[{u'menuText':self.com1_menuText, u'commands':self.failure_com1_commands, u'position':10, u'needSudo':False, u'FalseTooltipText':u'test'}]
	# 	self.failure_com1_noParentMenuText=[{u'menuText':self.com1_menuText, u'commands':self.failure_com1_commands, u'position':10, u'needSudo':False, u'tooltipText':u'test', u'FalseParentMenu':u'test'}]
	# 	with workWithEmptyCommandFile(self.backend._backend):
	# 		self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, self.failure_com1_noMenuText)
	# 		# self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, self.failure_com1_noCommands)
	# 		# self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, self.failure_com1_noPosition)
	# 		# self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, self.failure_com1_noNeedSudo)
	# 		# self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, self.failure_com1_noTooltipText)
	# 		# self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, self.failure_com1_noParentMenuText)

	# def testExceptionsValueUpdateObjects(self):
	# 	with workWithEmptyCommandFile(self.backend._backend):
	# 		self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, u'[this, is, not, a list]')
	# 		self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, None)
	# 		self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, [])
	# 		self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, [u'{this:is}', u'{not a : dictionary}'])
	# def testExceptionsValueUpdateObjects3(self):
	# 	self.failure_com1_menuTextFalseType=[{u'menuText':self.failure_com1_menuText, u'commands':self.failure_com1_commands}]
	# 	with workWithEmptyCommandFile(self.backend._backend):
	# 		self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, self.failure_com1_menuTextFalseType)
			
	# def testExceptionsValueUpdateObjects4(self):
	# 	self.failure_com1_commandsFalseType=[{u'menuText':self.com1_menuText, u'commands':self.failure_com1_commands}]
	# 	with workWithEmptyCommandFile(self.backend._backend):
	# 		self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, self.failure_com1_commandsFalseType)

	# def testExceptionsValueUpdateObjects1(self):
	# 	self.failure_com1_positionFalseType=[{u'menuText':self.com1_menuText, u'commands':self.com1_commands, u'position':u'test'}]
	# 	with workWithEmptyCommandFile(self.backend._backend):
	# 		self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, self.failure_com1_positionFalseType)
			
	# def testExceptionsValueUpdateObjects2(self):
	# 	self.failure_com1_needSudoFalseType=[{u'menuText':self.com1_menuText, u'commands':self.com1_commands, u'position':0, u'needSudo':u'shouldBeBool'}]
	# 	with workWithEmptyCommandFile(self.backend._backend):
	# 		self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, self.failure_com1_needSudoFalseType)

	# # def testExceptionsValueUpdateObjects5(self):
	# # 	self.failure_com1_tooltipTextFalseType=[{u'menuText':self.com1_menuText, u'commands':self.com1_commands, u'position':0, u'needSudo':True, u'tooltipText':True}]
	# # 	with workWithEmptyCommandFile(self.backend._backend):
	# # 		self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, self.failure_com1_tooltipTextFalseType)
	# def testExceptionsValueUpdateObjects6(self):
	# 	self.failure_com1_parentMenuTextFalseType=[{u'menuText':self.com1_menuText, u'commands':self.com1_commands, u'position':0, u'needSudo':True, u'tooltipText':u'', u'parentMenuText':False}]
	# 	with workWithEmptyCommandFile(self.backend._backend):
	# 		self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, self.failure_com1_parentMenuTextFalseType)

	# def testExceptionsDeleteObject(self):
	# 	with workWithEmptyCommandFile(self.backend._backend):
	# 		self.assertEqual(self.backend.SSHCommand_getObjects(), [], "first return of SSHCommand_getObjects should be an empty list")
	# 		self.assertRaises(Exception, self.backend.SSHCommand_deleteObject, u'')
	# 		self.assertRaises(Exception, self.backend.SSHCommand_deleteObject, u'test') # Funktioniert nicht, da nicht existiert
	# 		self.assertRaises(Exception, self.backend.SSHCommand_deleteObject, [])
	# 		self.assertRaises(Exception, self.backend.SSHCommand_deleteObject, {})
	# 		self.assertRaises(Exception, self.backend.SSHCommand_deleteObject, None)
	# 		self.assertRaises(Exception, self.backend.SSHCommand_deleteObject, 100)
	# 		self.assertRaises(Exception, self.backend.SSHCommand_deleteObject, False)

	# def testExceptionsDeleteObjects(self):
	# 	with workWithEmptyCommandFile(self.backend._backend):
	# 		self.assertEqual(self.backend.SSHCommand_getObjects(), [], "first return of SSHCommand_getObjects should be an empty list")
	# 		self.assertRaises(Exception, self.backend.SSHCommand_deleteObjects, u'')
	# 		self.assertRaises(Exception, self.backend.SSHCommand_deleteObjects, u'test')
	# 		self.assertRaises(Exception, self.backend.SSHCommand_deleteObjects, [])
	# 		self.assertRaises(Exception, self.backend.SSHCommand_deleteObjects, [u'Test']) # Funktioniert nicht, da nicht existiert
	# 		self.assertRaises(Exception, self.backend.SSHCommand_deleteObjects, {})
	# 		self.assertRaises(Exception, self.backend.SSHCommand_deleteObjects, None)
	# 		self.assertRaises(Exception, self.backend.SSHCommand_deleteObjects, 100)
	# 		self.assertRaises(Exception, self.backend.SSHCommand_deleteObjects, False)



if __name__ == '__main__':
	unittest.main()