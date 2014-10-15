#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2014 uib GmbH <info@uib.de>

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
Manual testrun for the commandline UI.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:author: Jan Schneider <j.schneider@uib.de>
:license: GNU Affero General Public License version 3
"""

import gettext
import sys
import time

from OPSI.UI import UIFactory

try:
    translation = gettext.translation('python-opsi', '/usr/share/locale')
    _ = translation.ugettext
except Exception as e:
    print(u"Locale not found: %s" % e)


    def _(string):
        """
        Fallback function for providing translations.
        """
        return string


if (__name__ == "__main__"):
    uiTest = UIFactory('snack')
    try:
        values = []
        for i in range(10):
            sel = False
            if i == 30: sel = True
            values.append( { "name": i, "selected": sel } )
        res = uiTest.getSelection(values, text = "Line1\nLine2\nLine3", radio=True, title = u"Please select")
        uiTest.showMessage(text = str(res), title = u'Message', width = 5, height = 5, seconds = 2)
    except Exception as e:
        uiTest.showMessage(text = str(e), title = u'Message', width = 5, height = 5, seconds = 2)

    try:
        values = []
        for i in range(10):
            sel = False
            if i == 30: sel = True
            values.append( { "name": i, "selected": sel } )
        res = uiTest.getSelection(values, radio=False, title = u"Please select")
        uiTest.showMessage(text = str(res), title = u'Message', width = 5, height = 5, seconds = 2)
    except Exception as e:
        uiTest.showMessage(text = str(e), title = u'Message', width = 5, height = 5, seconds = 2)

    uiTest.drawRootText(x = 1, y = 1, text = u'Test ä root text')
    uiTest.drawRootText(x = 1, y = 2, text = u'Test root text 2')
    uiTest.drawRootText(x = 5, y = 5, text = u'Test root text 3')
    time.sleep(1)
    uiTest.createMessageBox(title = "TEST").show()
    time.sleep(1)

    uiTest.showError(text = u'Test error', title = u'An error occured', okLabel = u'Read', width = -1, height = -1, seconds = 2)
    uiTest.showError(text = u'Test error äöü', title = u'An €rror occured', okLabel = u'ÖK', width = 30, height = 10)
    uiTest.showMessage(text = u'A message', title = u'Message', width = 5, height = 5, seconds = 2)
    uiTest.showMessage(text = u'Ä$§€€üüüüüüüüßßßßßßßßßß', title = u'Titel ä', okLabel = u'ÖK', width = -1, height = -1, seconds = 0)
    pb = uiTest.createProgressBox(width = -1, height = -1, total = 100, title = u'Progress', text = u'please wait')
    state = 0
    while (state < 100):
        state += 10
        pb.setState(state)
        time.sleep(0.5)
    time.sleep(2)

    pb = uiTest.createProgressBox(width = 30, height = 10, total = 200, title = u'Prögress', text = u'please wäit')
    state = 0
    while (state < 200):
        state += 20
        pb.setState(state)
        time.sleep(0.5)
    time.sleep(1)

    mb = uiTest.createMessageBox(width = -1, height = -1, title = u'€€€€€€€€', text = u'@&%$§"ß')
    mb.show()
    time.sleep(1)
    mb.setText(u'New text äöü')
    time.sleep(1)
    mb.addText(u'a\nü\nß\n')
    time.sleep(1)

    mb2 = uiTest.createMessageBox(width = 30, height = 20, title = u'smaller window', text = u'text\ntext\ntext')
    mb2.show()

    time.sleep(1)
    mbx = uiTest.getMessageBox()
    mbx.addText(u'\n\nTEST\nßßßßßßßßßßßßßßßßßßßß')
    mbx.show(seconds = 1)

    value = uiTest.getValue(width = 20, height = 10, title = u'€ Bitte text eingeben €', default = u'äääää', password = False, text = u'Bitte text eingeben üüüü', okLabel = u'ÖK', cancelLabel = u'Cäncel')
    mbx = uiTest.getMessageBox()
    mbx.setText(u'Got value: %s' % value)
    mbx.show(seconds = 1)

    entries = [ { 'name': u'€ntry 1', 'selected': False }, { 'name': u'€ntry 2', 'selected': True }, { 'name': u'€ntry 3', 'selected': True } ]
    selection = uiTest.getSelection(entries, radio = False, width = 20, height = 20, title = u'Select one or more entries', text = u'ßßßß', okLabel = u'ÖK', cancelLabel = u'Cäncel')
    mbx.setText(u'Got selection: %s' % selection)
    mbx.show(seconds = 1)

    entries = [ { 'name': u'€ntry 1', 'selected': False }, { 'name': u'€ntry 2', 'selected': True }, { 'name': u'€ntry 3', 'selected': True } ]
    selection = uiTest.getSelection(entries, radio = True, width = 20, height = 20, title = u'Select äntry', text = u'ßßßß', okLabel = u'ÖK', cancelLabel = u'Cäncel')
    mbx.setText(u'Got selection: %s' % selection)
    mbx.show(seconds = 1)

    entries = [ { 'name': u'€ntry 1', 'value': False }, { 'name': u'€ntry 2', 'value': [1, '2', 'üö'], 'multivalue': True }, { 'name': u'€ntry 3', 'value': u'söme value' } ]
    values = uiTest.getValues(entries, width = 30, title = u'Select välues', text = u'ßßßß', okLabel = u'ÖK', cancelLabel = u'Cäncel')
    uiTest.showMessage(text = u'Got values: %s' % values, title = u'Titel', okLabel = u'ÖK', width = -1, height = -1, seconds = 10)

    answer = uiTest.yesno(text = u'Täxt', title = u'Yäs Or Nö', okLabel = u'ÖK', cancelLabel = u'Cäncel', width = -1, height = -1)
    uiTest.showMessage(text = u'Answer was: %s' % answer, seconds = 2)

    uiTest.showError(text=_(u'Nothing selected'), title=_(u'An error occured'), okLabel=_(u'OK'), width=-1, height=-1, seconds=0)
    uiTest.showMessage(text = u'Answer was: %s' % _(u'Nothing selected'), seconds = 2)

    time.sleep(2)
    uiTest.exit()
