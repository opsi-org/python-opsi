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
import unittest


class SSHCommandsTestCase(unittest.TestCase, FileBackendBackendManagerMixin):
        """
        Testing the crud methods for json commands .
        """
        def setUp(self):
                self.setUpBackend()
                
                # self.backend._deleteSshCommandFileContent()
                self.name1=u'ÚTestName1'
                self.menuText1=u'UTestMenu1'
                self.command1={u'name':self.name1, u'menuText':self.menuText1}

                self.name2=u'TUestName2'
                self.menuText2=u'UTestMenu2'
                self.command2={u'name':self.name2, u'menuText':self.menuText2}

                self.name3=u'UTestName3'
                self.menuText3=u'UTestMenu3'
                self.command3={u'name':self.name3, u'menuText':self.menuText3}
                # self.commands=[u'test1', u'test2']
                # self.needSudo=True
                # self.priority=1
                # self.tooltip=u''
                # self.parentMenu=None
                self.commandlist=[]
                self.commandlist.append(self.command1)


        def tearDown(self):
                self.tearDownBackend()

        def testCreateCommand(self):
                # self.backend._deleteSshCommandFileContent()        
                # self.backend.createCommand(self.command1["name"], self.command1["menuText"]) 
                self.backend.createCommands(self.commandlist) 

                #, self.commands, self.needSudo, self.priority )
                # self.assertRaises(self.backend.createCommand(self.command1["name"], self.command1["menuText"]), Exception )
                self.assertEquals(self.backend.readCommands() , self.commandlist)
                self.assertNotEquals(self.backend.readCommands() , self.command2)

        # def testDeleteCommand(self):
        #         # self.backend.createCommand(name1, self.menuText, self.commands, self.needSudo, self.priority )
        #         # self.backend.createCommand(name2, self.menuText, self.commands, self.needSudo, self.priority )
        #         self.backend.createCommand(self.command1["name"], self.command1.["menuText"])
        #         self.backend.createCommand(self.command2["name"], self.command2.["menuText"])
        #         self.backend.createCommand(self.command3["name"], self.command3.["menuText"])
        #         self.backend.deleteCommand(self.command2["name"])
        #         commands=self.backend.readCommands()

        #         self.assertFalse(self.backend.getCommand(name1), commands)
        #         self.assertTrue(self.backend.getCommand(name2), commands)
        #         # self.assert()



if __name__ == '__main__':
    unittest.main()
