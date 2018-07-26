# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org

# Copyright (C) 2018 uib GmbH - http://www.uib.de/

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
E-Mail-Notifications for installed packages.

:copyright: uib GmbH <info@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import email.utils
import smtplib

from OPSI.Logger import Logger
from OPSI.Types import forceInt, forceUnicode, forceUnicodeList

logger = Logger()


class EmailNotifier(object):
	def __init__(self, smtphost=u'localhost', smtpport=25, subject=u'opsi product updater', sender=u'', receivers=[]):
		self.receivers = forceUnicodeList(receivers)
		if not self.receivers:
			raise ValueError(u"List of mail recipients empty")
		self.smtphost = forceUnicode(smtphost)
		self.smtpport = forceInt(smtpport)
		self.sender = forceUnicode(sender)
		self.subject = forceUnicode(subject)
		self.message = u''
		self.username = None
		self.password = None
		self.useStarttls = False

	def appendLine(self, line, pre=''):
		now = unicode(time.strftime(u"%b %d %H:%M:%S", time.localtime()), 'utf-8', 'replace')
		self.message += u'%s%s %s\n' % (pre, now, forceUnicode(line))

	def hasMessage(self):
		return bool(self.message)

	def notify(self):
		logger.notice(u"Sending mail notification")
		mail = u'From: %s\n' % self.sender
		mail += u'To: %s\n' % u','.join(self.receivers)
		mail += u'Date: {0}\n'.format(email.utils.formatdate(localtime=True))
		mail += u'Subject: %s\n' % self.subject
		mail += u'\n'
		# mail += _(u"opsi product updater carried out the following actions:") + u"\n"
		mail += self.message
		smtpObj = None
		try:
			smtpObj = smtplib.SMTP(self.smtphost, self.smtpport)
			smtpObj.ehlo_or_helo_if_needed()

			if self.useStarttls:
				if smtpObj.has_extn('STARTTLS'):
					logger.debug('Enabling STARTTLS')
					smtpObj.starttls()
				else:
					logger.debug('Server does not support STARTTLS.')

			if self.username and self.password is not None:
				logger.debug(
					'Trying to authenticate against SMTP server '
					'{host}:{port} as user "{username}"'.format(
						host=self.smtphost,
						port=self.smtpport,
						username=self.username
					)
				)
				smtpObj.login(self.username, self.password)
				smtpObj.ehlo_or_helo_if_needed()

			smtpObj.sendmail(self.sender, self.receivers, mail)
			logger.debug(u"SMTP-Host: '%s' SMTP-Port: '%s'" % (self.smtphost, self.smtpport))
			logger.debug(u"Sender: '%s' Reveivers: '%s' Message: '%s'" % (self.sender, self.receivers, mail))
			logger.notice(u"Email successfully sent")
			smtpObj.quit()
		except Exception as error:
			if smtpObj is not None:
				logger.debug('SMTP Server does esmtp: {0}'.format(smtpObj.does_esmtp))
				if hasattr(smtpObj, 'ehlo_resp'):
					logger.debug('SMTP EHLO response: {0}'.format(smtpObj.ehlo_resp))

				if hasattr(smtpObj, 'esmtp_features'):
					logger.debug('ESMTP Features: {0}'.format(smtpObj.esmtp_features))

			raise RuntimeError(u"Failed to send email using smtp server '%s': %s" % (self.smtphost, error))
