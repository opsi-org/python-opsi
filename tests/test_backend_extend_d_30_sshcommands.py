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
import unittest, json
from contextlib import contextmanager
# import unittest, json

@contextmanager
def workWithEmptyCommandFile(backend):
	with workInTemporaryDirectory():
		filename = u'test_file.conf'
		filenames = [filename]
		with open(filename, "w"):
			pass
		with mock.patch.object(backend, '_getSSHCommandCustomFilename', return_value=filename):
			yield
		with mock.patch.object(backend, '_getSSHCommandFilenames', return_value=[filename]):
			yield

@contextmanager
def workWithBrokenCommandFile(backend):
	 import json
	 with workInTemporaryDirectory():
		filename = u'test_file.conf'
		# filenames =[filename]
		element = {"id":"rechte_setzen", "menuText : Rechte setzen":"", "commands":["opsi-set-rights"], "position":30,"needSudo":True, "tooltipText":"Rechte mittels opsi-set-rights setzen", "parentMenuText":"opsi"}
		with open(filename, "w") as f:
			json.dump(element, f)
		with mock.patch.object(backend, '_getSSHCommandCustomFilename', return_value=filename):
			yield
		with mock.patch.object(backend, '_getSSHCommandFilenames', return_value=[filename]):
			yield

class SSHCommandsTestCase(unittest.TestCase, FileBackendBackendManagerMixin):
	"""
	Testing the crud methods for json commands .
	"""
	def setUp(self):
		self.setUpBackend()
		self.com1_id=u'utestmenu1'
		self.com1_menuText=u'UTestMenu1'
		self.com1_commands=[u'test 1']
		self.com1_position=5
		self.com1_needSudo=True
		self.com1_tooltipText=u'Test Tooltip1'
		self.com1_parentMenuText=u'Test Parent1'
		self.com1={u'menuText':self.com1_menuText, u'commands':self.com1_commands}
		self.com1_full={u'id':self.com1_id, u'menuText':self.com1_menuText, u'commands':self.com1_commands, u'needSudo':self.com1_needSudo, u'position':self.com1_position, u'tooltipText':self.com1_tooltipText, u'parentMenuText':self.com1_parentMenuText}

		self.com2_id=u'utestmenu2'
		self.com2_menuText=u'UTestMenu2'
		self.com2_commands=[u'test 2']
		self.com2_position=52
		self.com2_needSudo=True
		self.com2_tooltipText=u'Test Tooltip2'
		self.com2_parentMenuText=u'Test Parent1'
		self.com2={u'menuText':self.com2_menuText, u'commands':self.com2_commands}
		self.com2_full={u'id':self.com2_id, u'menuText':self.com2_menuText, u'commands':self.com2_commands, u'needSudo':self.com2_needSudo, u'position':self.com2_position, u'tooltipText':self.com2_tooltipText, u'parentMenuText':self.com2_parentMenuText}

		self.com3_id=u'utestmenu3'
		self.com3_menuText=u'UTestMenu3'
		self.com3_commands=[u'test 3']
		self.com3_position=53
		self.com3_needSudo=True
		self.com3_tooltipText=u'Test Tooltip3'
		self.com3_parentMenuText=u'Test Parent3'
		self.com3={u'menuText':self.com3_menuText, u'commands':self.com3_commands}
		self.com3_full={u'id':self.com3_id, u'menuText':self.com3_menuText, u'commands':self.com3_commands, u'needSudo':self.com3_needSudo, u'position':self.com3_position, u'tooltipText':self.com3_tooltipText, u'parentMenuText':self.com3_parentMenuText}

		self.commandlist_menuTexts_1=[self.com1_menuText]
		self.commandlist_menuTexts_12=[self.com1_menuText, self.com2_menuText]
		self.commandlist_menuTexts_123=[self.com1_menuText, self.com2_menuText, self.com3_menuText]

		self.commandlist_com1=[self.com1]
		self.commandlist_com2=[self.com2]
		self.commandlist_com3=[self.com3]
		self.commandlist_com11=[self.com1, self.com1]
		self.commandlist_com12=[self.com1, self.com2]
		self.commandlist_com123=[self.com1, self.com2, self.com3]

		self.commandlist_com1_full=[self.com1_full]
		self.commandlist_com2_full=[self.com2_full]
		self.commandlist_com3_full=[self.com3_full]
		self.commandlist_com12_full=[self.com1_full,self.com2_full]
		self.commandlist_com123_full=[self.com1_full,self.com2_full, self.com3_full]

		self.def_position=0
		self.def_needSudo=False
		self.def_tooltipText=u''
		self.def_parentMenuText=None
		self.com1_with_defval={u'id':self.com1_id, u'menuText':self.com1_menuText, u'commands':self.com1_commands, u'needSudo':self.def_needSudo, u'position':self.def_position, u'tooltipText':self.def_tooltipText, u'parentMenuText':self.def_parentMenuText}
		self.com2_with_defval={u'id':self.com2_id, u'menuText':self.com2_menuText, u'commands':self.com2_commands, u'needSudo':self.def_needSudo, u'position':self.def_position, u'tooltipText':self.def_tooltipText, u'parentMenuText':self.def_parentMenuText}
		self.com3_with_defval={u'id':self.com3_id, u'menuText':self.com3_menuText, u'commands':self.com3_commands, u'needSudo':self.def_needSudo, u'position':self.def_position, u'tooltipText':self.def_tooltipText, u'parentMenuText':self.def_parentMenuText}
		# self.commandlist_com11=[self.com1, self.com1]

		self.commandlist_com1_withdefval_full=[self.com1_with_defval]
		self.commandlist_com2_withdefval_full=[self.com2_with_defval]
		self.commandlist_com3_withdefval_full=[self.com3_with_defval]
		self.commandlist_com12_withdefval_full=[self.com1_with_defval,self.com2_with_defval]
		self.commandlist_com123_withdefval_full=[self.com1_with_defval,self.com2_with_defval,self.com3_with_defval]


		self.failure_com1_id=u'utestmenu1'
		self.failure_com1_menuText=20
		self.failure_com1_commands=u'test 1'
		self.failure_com1_position=u'O'
		self.failure_com1_needSudo=u'True'
		self.failure_com1_tooltipText=False
		self.failure_com1_parentMenuText=False

	def tearDown(self):
		self.tearDownBackend()

	# def testExceptionGetCommand(self):
	# 	with workWithBrokenCommandFile(self.backend._backend):
	# 		self.assertRaises(Exception, self.backend.SSHCommand_deleteObjects)

	def testGetCommand(self):
		with workWithEmptyCommandFile(self.backend._backend):
			self.assertEqual(self.backend.SSHCommand_getObjects(), [], "first return of SSHCommand_getObjects should be an empty list")
			self.assertListEqual(self.backend.SSHCommand_createObjects( self.commandlist_com1), self.commandlist_com1_withdefval_full)
			self.assertListEqual(self.backend.SSHCommand_getObjects(), self.commandlist_com1_withdefval_full)

	def testCreateCommand(self):
		with workWithEmptyCommandFile(self.backend._backend):
			self.assertEqual(self.backend.SSHCommand_getObjects(), [], "first return of SSHCommand_getObjects should be an empty list")
			return_value = self.backend.SSHCommand_createObject( self.com1["menuText"], self.com1["commands"])
			self.assertListEqual(return_value, self.commandlist_com1_withdefval_full)

	def testCreateCommands(self):
		with workWithEmptyCommandFile(self.backend._backend):
			self.assertEqual(self.backend.SSHCommand_getObjects(), [], "first return of SSHCommand_getObjects should be an empty list")
			self.assertListEqual(self.backend.SSHCommand_createObjects( self.commandlist_com1), self.commandlist_com1_withdefval_full)
		with workWithEmptyCommandFile(self.backend._backend):
			self.assertEqual(self.backend.SSHCommand_getObjects(), [], "first return of SSHCommand_getObjects should be an empty list")
			self.assertListEqual(self.backend.SSHCommand_createObjects( self.commandlist_com12), self.commandlist_com12_withdefval_full)
		with workWithEmptyCommandFile(self.backend._backend):
			self.assertEqual(self.backend.SSHCommand_getObjects(), [], "first return of SSHCommand_getObjects should be an empty list")
			self.assertListEqual(self.backend.SSHCommand_createObjects( self.commandlist_com123), self.commandlist_com123_withdefval_full)

	def testUpdateCommand(self):
		with workWithEmptyCommandFile(self.backend._backend):
			self.assertEqual(self.backend.SSHCommand_getObjects(), [], "first return of SSHCommand_getObjects should be an empty list")
			self.backend.SSHCommand_createObject( self.com1["menuText"], self.com1["commands"])
			self.commandlist_com1_full[0]["commands"]=new_commands=[u'MyNewTestCom']
			self.commandlist_com1_full[0]["position"]=new_position=10
			self.commandlist_com1_full[0]["needSudo"]=new_needSudo=True
			self.commandlist_com1_full[0]["tooltipText"]=new_tooltipText=u'MyNewTooltipText'
			self.commandlist_com1_full[0]["parentMenuText"]=new_parentMenuText=u'myParent'
			return_command = self.backend.SSHCommand_updateObject( self.com1["menuText"], new_commands, new_position, new_needSudo, new_tooltipText, new_parentMenuText)
			self.assertListEqual(return_command, self.commandlist_com1_full)

	def testUpdateCommands(self):
		with workWithEmptyCommandFile(self.backend._backend):
			self.assertEqual(self.backend.SSHCommand_getObjects(), [], "first return of SSHCommand_getObjects should be an empty list")
			self.backend.SSHCommand_createObjects( self.commandlist_com12)
			self.commandlist_com123_full[0]["commands"]=new_commands1=[u'MyNewTestCom1']
			self.commandlist_com123_full[0]["position"]=new_position1=11
			self.commandlist_com123_full[0]["needSudo"]=new_needSudo1=True
			self.commandlist_com123_full[0]["tooltipText"]=new_tooltipText1=u'MyNewTooltipText1'
			self.commandlist_com123_full[0]["parentMenuText"]=new_parentMenuText1=u'myParent1'
			self.commandlist_com123_full[1]["commands"]=new_commands2=[u'MyNewTestCom2']
			self.commandlist_com123_full[1]["position"]=new_position2=12
			self.commandlist_com123_full[1]["needSudo"]=new_needSudo2=True
			self.commandlist_com123_full[1]["tooltipText"]=new_tooltipText2=u'MyNewTooltipText2'
			self.commandlist_com123_full[1]["parentMenuText"]=new_parentMenuText2=u'myParent2'
			self.commandlist_com123_full[2]["commands"]=new_commands3=[u'MyNewTestCom3']
			self.commandlist_com123_full[2]["position"]=new_position3=13
			self.commandlist_com123_full[2]["needSudo"]=new_needSudo3=True
			self.commandlist_com123_full[2]["tooltipText"]=new_tooltipText3=u'MyNewTooltipText3'
			self.commandlist_com123_full[2]["parentMenuText"]=new_parentMenuText3=u'myParent3'
			return_command = self.backend.SSHCommand_updateObjects( self.commandlist_com123_full)
			self.assertListEqual(return_command, self.commandlist_com123_full)

	def testDeleteCommand(self):
		with workWithEmptyCommandFile(self.backend._backend):
			self.assertEqual(self.backend.SSHCommand_getObjects(), [], "first return of SSHCommand_getObjects should be an empty list")
			self.assertListEqual(self.backend.SSHCommand_createObjects( self.commandlist_com12), self.commandlist_com12_withdefval_full)
			self.assertListEqual(self.backend.SSHCommand_deleteObject(self.com2_menuText), self.commandlist_com1_withdefval_full)

	def testDeleteCommands(self):
		with workWithEmptyCommandFile(self.backend._backend):
			self.assertEqual(self.backend.SSHCommand_getObjects(), [], "first return of SSHCommand_getObjects should be an empty list")
			self.assertListEqual(self.backend.SSHCommand_createObjects( self.commandlist_com123), self.commandlist_com123_withdefval_full)
			self.assertListEqual(self.backend.SSHCommand_deleteObjects(self.commandlist_menuTexts_123), [])
		with workWithEmptyCommandFile(self.backend._backend):
			self.assertEqual(self.backend.SSHCommand_getObjects(), [], "first return of SSHCommand_getObjects should be an empty list")
			self.assertListEqual(self.backend.SSHCommand_createObjects( self.commandlist_com123), self.commandlist_com123_withdefval_full)
			self.assertListEqual(self.backend.SSHCommand_deleteObjects(self.commandlist_menuTexts_12), self.commandlist_com3_withdefval_full)

	def testExceptionsCreateObject(self):
		with workWithEmptyCommandFile(self.backend._backend):
			self.assertRaises(Exception, self.backend.SSHCommand_createObject, None, None)
			self.assertRaises(Exception, self.backend.SSHCommand_createObject, self.com1_menuText, self.failure_com1_commands)
			self.assertRaises(Exception, self.backend.SSHCommand_createObject, self.com1_menuText, self.com1_commands, self.failure_com1_position)
			self.assertRaises(Exception, self.backend.SSHCommand_createObject, self.com1_menuText, self.com1_commands, self.com1_position, self.failure_com1_needSudo)
			self.assertRaises(Exception, self.backend.SSHCommand_createObject, self.com1_menuText, self.com1_commands, self.com1_position, self.com1_needSudo, self.failure_com1_tooltipText)
			self.assertRaises(Exception, self.backend.SSHCommand_createObject, self.com1_menuText, self.com1_commands, self.com1_position, self.com1_needSudo, self.com1_tooltipText, self.failure_com1_parentMenuText)
			self.assertListEqual(self.backend.SSHCommand_createObjects( self.commandlist_com1), self.commandlist_com1_withdefval_full)
			self.assertRaises(Exception, self.backend.SSHCommand_createObject, self.com1_menuText, self.com1_commands, self.com1_position, self.com1_needSudo, self.com1_tooltipText, self.com1_parentMenuText)

	def testExceptionsCreateObjects(self):
		self.failure_com1_noMenuText=[{u'FailureMenuText':self.com1_menuText, u'commands':self.failure_com1_commands}]
		self.failure_com1_menuTextFalseType=[{u'menuText':self.failure_com1_menuText, u'commands':self.failure_com1_commands}]
		self.failure_com1_noCommands=[{u'menuText':self.com1_menuText, u'falseCommands':self.com1_commands}]
		self.failure_com1_commandsFalseType=[{u'menuText':self.com1_menuText, u'commands':self.failure_com1_commands}]
		with workWithEmptyCommandFile(self.backend._backend):
			self.assertRaises(Exception, self.backend.SSHCommand_createObjects, u'[this, is, not, a list]')
			self.assertRaises(Exception, self.backend.SSHCommand_createObjects, [])
			self.assertRaises(Exception, self.backend.SSHCommand_createObjects, [u'{this:is}', u'{not a : dictionary}'])
			self.assertRaises(Exception, self.backend.SSHCommand_createObjects, self.failure_com1_noMenuText)
			self.assertRaises(Exception, self.backend.SSHCommand_createObjects, self.failure_com1_noCommands)
			self.assertRaises(Exception, self.backend.SSHCommand_createObjects, self.failure_com1_menuTextFalseType)
			self.assertRaises(Exception, self.backend.SSHCommand_createObjects, self.failure_com1_commandsFalseType)
			self.assertRaises(Exception, self.backend.SSHCommand_createObjects, self.commandlist_com11)

	def testExceptionsUpdateObject(self):
		with workWithEmptyCommandFile(self.backend._backend):
			self.assertRaises(Exception, self.backend.SSHCommand_updateObject, None, None)
			self.assertRaises(Exception, self.backend.SSHCommand_updateObject, self.com1_menuText, self.failure_com1_commands)
			self.assertRaises(Exception, self.backend.SSHCommand_updateObject, self.com1_menuText, self.com1_commands, self.failure_com1_position)
			self.assertRaises(Exception, self.backend.SSHCommand_updateObject, self.com1_menuText, self.com1_commands, self.com1_position, self.failure_com1_needSudo)
			self.assertRaises(Exception, self.backend.SSHCommand_updateObject, self.com1_menuText, self.com1_commands, self.com1_position, self.com1_needSudo, self.failure_com1_tooltipText)
			self.assertRaises(Exception, self.backend.SSHCommand_updateObject, self.com1_menuText, self.com1_commands, self.com1_position, self.com1_needSudo, self.com1_tooltipText, self.failure_com1_parentMenuText)
			#self.assertListEqual(self.backend.SSHCommand_createObjects( self.commandlist_com1), self.commandlist_com1_withdefval_full)
			#self.assertRaises(Exception, self.backend.SSHCommand_updateObject, self.com1_menuText, self.com1_commands, self.com1_position, self.com1_needSudo, self.com1_tooltipText, self.com1_parentMenuText)

	def testExceptionsKeysUpdateObjects(self):
		self.failure_com1_noMenuText=[{u'FailureMenuText':self.com1_menuText, u'commands':self.failure_com1_commands}]
		self.failure_com1_noCommands=[{u'menuText':self.com1_menuText, u'falseCommands':self.com1_commands}]
		self.failure_com1_noPosition=[{u'menuText':self.com1_menuText, u'commands':self.failure_com1_commands, u'falsePosition':10}]
		self.failure_com1_noNeedSudo=[{u'menuText':self.com1_menuText, u'commands':self.failure_com1_commands, u'position':10, u'FalseNeedSudo':False}]
		self.failure_com1_noTooltipText=[{u'menuText':self.com1_menuText, u'commands':self.failure_com1_commands, u'position':10, u'needSudo':False, u'FalseTooltipText':u'test'}]
		self.failure_com1_noParentMenuText=[{u'menuText':self.com1_menuText, u'commands':self.failure_com1_commands, u'position':10, u'needSudo':False, u'tooltipText':u'test', u'FalseParentMenu':u'test'}]
		with workWithEmptyCommandFile(self.backend._backend):
			self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, u'[this, is, not, a list]')
			self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, None)
			self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, [])
			self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, [u'{this:is}', u'{not a : dictionary}'])
			self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, self.failure_com1_noMenuText)
			self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, self.failure_com1_noCommands)
			self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, self.failure_com1_noPosition)
			self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, self.failure_com1_noNeedSudo)
			self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, self.failure_com1_noTooltipText)
			self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, self.failure_com1_noParentMenuText)

	def testExceptionsValueUpdateObjects(self):
		self.failure_com1_menuTextFalseType=[{u'menuText':self.failure_com1_menuText, u'commands':self.failure_com1_commands}]
		self.failure_com1_commandsFalseType=[{u'menuText':self.com1_menuText, u'commands':self.failure_com1_commands}]
		self.failure_com1_positionFalseType=[{u'menuText':self.com1_menuText, u'commands':self.com1_commands, u'position':u'test'}]
		self.failure_com1_needSudoFalseType=[{u'menuText':self.com1_menuText, u'commands':self.com1_commands, u'position':0, u'needSudo':u'shouldBeBool'}]
		self.failure_com1_tooltipTextFalseType=[{u'menuText':self.com1_menuText, u'commands':self.com1_commands, u'position':0, u'needSudo':True, u'tooltipText':True}]
		self.failure_com1_parentMenuTextFalseType=[{u'menuText':self.com1_menuText, u'commands':self.com1_commands, u'position':0, u'needSudo':True, u'tooltipText':u'', u'parentMenuText':False}]
		with workWithEmptyCommandFile(self.backend._backend):
			self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, u'[this, is, not, a list]')
			self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, None)
			self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, [])
			self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, [u'{this:is}', u'{not a : dictionary}'])
			self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, self.failure_com1_menuTextFalseType)
			self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, self.failure_com1_commandsFalseType)
			self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, self.failure_com1_positionFalseType)
			self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, self.failure_com1_needSudoFalseType)
			self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, self.failure_com1_tooltipTextFalseType)
			self.assertRaises(Exception, self.backend.SSHCommand_updateObjects, self.failure_com1_parentMenuTextFalseType)

	def testExceptionsDeleteObject(self):
		with workWithEmptyCommandFile(self.backend._backend):
			self.assertEqual(self.backend.SSHCommand_getObjects(), [], "first return of SSHCommand_getObjects should be an empty list")
			self.assertRaises(Exception, self.backend.SSHCommand_deleteObject, u'')
			self.assertRaises(Exception, self.backend.SSHCommand_deleteObject, u'test') # Funktioniert nicht, da nicht existiert
			self.assertRaises(Exception, self.backend.SSHCommand_deleteObject, [])
			self.assertRaises(Exception, self.backend.SSHCommand_deleteObject, {})
			self.assertRaises(Exception, self.backend.SSHCommand_deleteObject, None)
			self.assertRaises(Exception, self.backend.SSHCommand_deleteObject, 100)
			self.assertRaises(Exception, self.backend.SSHCommand_deleteObject, False)

	def testExceptionsDeleteObjects(self):
		with workWithEmptyCommandFile(self.backend._backend):
			self.assertEqual(self.backend.SSHCommand_getObjects(), [], "first return of SSHCommand_getObjects should be an empty list")
			self.assertRaises(Exception, self.backend.SSHCommand_deleteObjects, u'')
			self.assertRaises(Exception, self.backend.SSHCommand_deleteObjects, u'test')
			self.assertRaises(Exception, self.backend.SSHCommand_deleteObjects, [])
			self.assertRaises(Exception, self.backend.SSHCommand_deleteObjects, [u'Test']) # Funktioniert nicht, da nicht existiert
			self.assertRaises(Exception, self.backend.SSHCommand_deleteObjects, {})
			self.assertRaises(Exception, self.backend.SSHCommand_deleteObjects, None)
			self.assertRaises(Exception, self.backend.SSHCommand_deleteObjects, 100)
			self.assertRaises(Exception, self.backend.SSHCommand_deleteObjects, False)



if __name__ == '__main__':
	unittest.main()