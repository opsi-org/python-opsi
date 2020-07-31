import re
import os
import time
import copy as pycopy

from OPSI.Types import (forceFilename, 
	forceHardwareDeviceId, forceHardwareVendorId, forceUnicode)
from OPSI.Util import  objectToBeautifiedText, removeUnit

from .Posix import logger, execute, which

def getBlockDeviceContollerInfo(device, lshwoutput=None):
	device = forceFilename(device)
	if lshwoutput and isinstance(lshwoutput, list):
		lines = lshwoutput
	else:
		lines = execute(u'%s -short -numeric' % which('lshw'))
	# example:
	# ...
	# /0/100                      bridge     440FX - 82441FX PMC [Natoma] [8086:1237]
	# /0/100/1                    bridge     82371SB PIIX3 ISA [Natoma/Triton II] [8086:7000]
	# /0/100/1.1      scsi0       storage    82371SB PIIX3 IDE [Natoma/Triton II] [8086:7010]
	# /0/100/1.1/0    /dev/sda    disk       10GB QEMU HARDDISK
	# /0/100/1.1/0/1  /dev/sda1   volume     10236MiB Windows NTFS volume
	# /0/100/1.1/1    /dev/cdrom  disk       SCSI CD-ROM
	# ...
	storageControllers = {}

	for line in lines:
		match = re.search(r'^(/\S+)\s+(\S+)\s+storage\s+(\S+.*)\s\[([a-fA-F0-9]{1,4}):([a-fA-F0-9]{1,4})\]$', line)
		if match:
			vendorId = match.group(4)
			while len(vendorId) < 4:
				vendorId = '0' + vendorId
			deviceId = match.group(5)
			while len(deviceId) < 4:
				deviceId = '0' + deviceId
			storageControllers[match.group(1)] = {
				'hwPath': forceUnicode(match.group(1)),
				'device': forceUnicode(match.group(2)),
				'description': forceUnicode(match.group(3)),
				'vendorId': forceHardwareVendorId(vendorId),
				'deviceId': forceHardwareDeviceId(deviceId)
			}
			continue

		parts = line.split(None, 3)
		if len(parts) < 4:
			continue

		if parts[1].lower() == device:
			for hwPath in storageControllers:
				if parts[0].startswith(hwPath + u'/'):
					return storageControllers[hwPath]


def hardwareInventory(config, progressSubject=None):
	import xml.dom.minidom

	if not config:
		logger.error(u"hardwareInventory: no config given")
		return {}

	opsiValues = {}

	def getAttribute(dom, tagname, attrname):
		nodelist = dom.getElementsByTagName(tagname)
		if nodelist:
			return nodelist[0].getAttribute(attrname).strip()
		else:
			return u""

	def getElementsByAttributeValue(dom, tagName, attributeName, attributeValue):
		return [element for element in dom.getElementsByTagName(tagName) if re.search(attributeValue, element.getAttribute(attributeName))]

	# Read output from lshw
	xmlOut = u'\n'.join(execute(u"%s -xml 2>/dev/null" % which("lshw")))
	xmlOut = re.sub('[%c%c%c%c%c%c%c%c%c%c%c%c%c]' % (0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0xbd, 0xbf, 0xef, 0xdd), u'.', xmlOut)
	dom = xml.dom.minidom.parseString(xmlOut.encode('utf-8'))

	# Read output from lspci
	lspci = {}
	busId = None
	devRegex = re.compile(r'([\d.:a-f]+)\s+([\da-f]+):\s+([\da-f]+):([\da-f]+)\s*(\(rev ([^\)]+)\)|)')
	subRegex = re.compile(r'\s*Subsystem:\s+([\da-f]+):([\da-f]+)\s*')
	for line in execute(u"%s -vn" % which("lspci")):
		if not line.strip():
			continue
		match = re.search(devRegex, line)
		if match:
			busId = match.group(1)
			lspci[busId] = {
				'vendorId': forceHardwareVendorId(match.group(3)),
				'deviceId': forceHardwareDeviceId(match.group(4)),
				'subsystemVendorId': '',
				'subsystemDeviceId': '',
				'revision': match.group(6) or ''
			}
			continue
		match = re.search(subRegex, line)
		if match:
			lspci[busId]['subsystemVendorId'] = forceHardwareVendorId(match.group(1))
			lspci[busId]['subsystemDeviceId'] = forceHardwareDeviceId(match.group(2))
	logger.debug2(u"Parsed lspci info:")
	logger.debug2(objectToBeautifiedText(lspci))

	# Read hdaudio information from alsa
	hdaudio = {}
	if os.path.exists('/proc/asound'):
		for card in os.listdir('/proc/asound'):
			if not re.search(r'^card\d$', card):
				continue
			logger.debug(u"Found hdaudio card '%s'", card)
			for codec in os.listdir('/proc/asound/' + card):
				if not re.search(r'^codec#\d$', codec):
					continue
				if not os.path.isfile('/proc/asound/' + card + '/' + codec):
					continue
				with open('/proc/asound/' + card + '/' + codec) as f:
					logger.debug(u"   Found hdaudio codec '%s'", codec)
					hdaudioId = card + codec
					hdaudio[hdaudioId] = {}
					for line in f:
						if line.startswith(u'Codec:'):
							hdaudio[hdaudioId]['codec'] = line.split(':', 1)[1].strip()
						elif line.startswith(u'Address:'):
							hdaudio[hdaudioId]['address'] = line.split(':', 1)[1].strip()
						elif line.startswith(u'Vendor Id:'):
							vid = line.split('x', 1)[1].strip()
							hdaudio[hdaudioId]['vendorId'] = forceHardwareVendorId(vid[0:4])
							hdaudio[hdaudioId]['deviceId'] = forceHardwareDeviceId(vid[4:8])
						elif line.startswith(u'Subsystem Id:'):
							sid = line.split('x', 1)[1].strip()
							hdaudio[hdaudioId]['subsystemVendorId'] = forceHardwareVendorId(sid[0:4])
							hdaudio[hdaudioId]['subsystemDeviceId'] = forceHardwareDeviceId(sid[4:8])
						elif line.startswith(u'Revision Id:'):
							hdaudio[hdaudioId]['revision'] = line.split('x', 1)[1].strip()
				logger.debug(u"      Codec info: '%s'", hdaudio[hdaudioId])

	# Read output from lsusb
	lsusb = {}
	busId = None
	devId = None
	indent = -1
	currentKey = None
	status = False

	devRegex = re.compile(r'^Bus\s+(\d+)\s+Device\s+(\d+):\s+ID\s+([\da-fA-F]{4}):([\da-fA-F]{4})\s*(.*)$')
	descriptorRegex = re.compile(r'^(\s*)(.*)\s+Descriptor:\s*$')
	deviceStatusRegex = re.compile(r'^(\s*)Device\s+Status:\s+(\S+)\s*$')
	deviceQualifierRegex = re.compile(r'^(\s*)Device\s+Qualifier\s+.*:\s*$')
	keyRegex = re.compile(r'^(\s*)([^\:]+):\s*$')
	keyValueRegex = re.compile(r'^(\s*)(\S+)\s+(.*)$')

	try:
		for line in execute(u"%s -v" % which("lsusb")):
			if not line.strip() or (line.find(u'** UNAVAILABLE **') != -1):
				continue
			# line = line.decode('ISO-8859-15', 'replace').encode('utf-8', 'replace')
			match = re.search(devRegex, line)
			if match:
				busId = str(match.group(1))
				devId = str(match.group(2))
				descriptor = None
				indent = -1
				currentKey = None
				status = False
				logger.debug(u"Device: %s:%s", busId, devId)
				# TODO: better key building.
				lsusb[busId + ":" + devId] = {
					'device': {},
					'configuration': {},
					'interface': {},
					'endpoint': [],
					'hid device': {},
					'hub': {},
					'qualifier': {},
					'status': {}
				}
				continue

			if status:
				lsusb[busId + ":" + devId]['status'].append(line.strip())
				continue

			match = re.search(deviceStatusRegex, line)
			if match:
				status = True
				lsusb[busId + ":" + devId]['status'] = [match.group(2)]
				continue

			match = re.search(deviceQualifierRegex, line)
			if match:
				descriptor = 'qualifier'
				logger.debug(u"Qualifier")
				currentKey = None
				indent = -1
				continue

			match = re.search(descriptorRegex, line)
			if match:
				descriptor = match.group(2).strip().lower()
				logger.debug(u"Descriptor: %s", descriptor)
				if isinstance(lsusb[busId + ":" + devId][descriptor], list):
					lsusb[busId + ":" + devId][descriptor].append({})
				currentKey = None
				indent = -1
				continue

			if not descriptor:
				logger.error(u"No descriptor")
				continue

			if descriptor not in lsusb[busId + ":" + devId]:
				logger.error(u"Unknown descriptor '%s'", descriptor)
				continue

			(key, value) = ('', '')
			match = re.search(keyRegex, line)
			if match:
				key = match.group(2)
				indent = len(match.group(1))
			else:
				match = re.search(keyValueRegex, line)
				if match:
					if indent >= 0 and len(match.group(1)) > indent:
						key = currentKey
						value = match.group(0).strip()
					else:
						(key, value) = (match.group(2), match.group(3).strip())
						indent = len(match.group(1))

			logger.debug(u"key: '%s', value: '%s'", key, value)

			if not key or not value:
				continue

			currentKey = key
			if isinstance(lsusb[busId + ":" + devId][descriptor], list):
				if key not in lsusb[busId + ":" + devId][descriptor][-1]:
					lsusb[busId + ":" + devId][descriptor][-1][key] = []
				lsusb[busId + ":" + devId][descriptor][-1][key].append(value)
			else:
				if key not in lsusb[busId + ":" + devId][descriptor]:
					lsusb[busId + ":" + devId][descriptor][key] = []
				lsusb[busId + ":" + devId][descriptor][key].append(value)

		logger.debug2(u"Parsed lsusb info:")
		logger.debug2(objectToBeautifiedText(lsusb))
	except Exception as e:
		logger.error(e)

	# Read output from dmidecode
	dmidecode = {}
	dmiType = None
	header = True
	option = None
	optRegex = re.compile(r'(\s+)([^:]+):(.*)')
	for line in execute(which("dmidecode")):
		try:
			if not line.strip():
				continue
			if line.startswith(u'Handle'):
				dmiType = None
				header = False
				option = None
				continue
			if header:
				continue
			if not dmiType:
				dmiType = line.strip()
				if dmiType.lower() == u'end of table':
					break
				if dmiType not in dmidecode:
					dmidecode[dmiType] = []
				dmidecode[dmiType].append({})
			else:
				match = re.search(optRegex, line)
				if match:
					option = match.group(2).strip()
					value = match.group(3).strip()
					dmidecode[dmiType][-1][option] = removeUnit(value)
				elif option:
					if not isinstance(dmidecode[dmiType][-1][option], list):
						if dmidecode[dmiType][-1][option]:
							dmidecode[dmiType][-1][option] = [dmidecode[dmiType][-1][option]]
						else:
							dmidecode[dmiType][-1][option] = []
					dmidecode[dmiType][-1][option].append(removeUnit(line.strip()))
		except Exception as e:
			logger.error(u"Error while parsing dmidecode output '%s': %s", line.strip(), e)
	logger.debug2(u"Parsed dmidecode info:")
	logger.debug2(objectToBeautifiedText(dmidecode))

	# Build hw info structure
	for hwClass in config:
		if not hwClass.get('Class') or not hwClass['Class'].get('Opsi') or not hwClass['Class'].get('Linux'):
			continue

		opsiClass = hwClass['Class']['Opsi']
		linuxClass = hwClass['Class']['Linux']

		logger.debug(u"Processing class '%s' : '%s'", opsiClass, linuxClass)

		if linuxClass.startswith('[lshw]'):
			# Get matching xml nodes
			devices = []
			for hwclass in linuxClass[6:].split('|'):
				hwid = ''
				filter = None
				if ':' in hwclass:
					(hwclass, hwid) = hwclass.split(':', 1)
					if ':' in hwid:
						(hwid, filter) = hwid.split(':', 1)

				logger.debug(u"Class is '%s', id is '%s', filter is: %s", hwClass, hwid, filter)

				devs = getElementsByAttributeValue(dom, 'node', 'class', hwclass)
				for dev in devs:
					if dev.hasChildNodes():
						for child in dev.childNodes:
							if child.nodeName == "businfo":
								busInfo = child.firstChild.data.strip()
								if busInfo.startswith('pci@'):
									logger.debug(u"Getting pci bus info for '%s'", busInfo)
									pciBusId = busInfo.split('@')[1]
									if pciBusId.startswith('0000:'):
										pciBusId = pciBusId[5:]
									pciInfo = lspci.get(pciBusId, {})
									for (key, value) in pciInfo.items():
										elem = dom.createElement(key)
										elem.childNodes.append(dom.createTextNode(value))
										dev.childNodes.append(elem)
								break
				if hwid:
					filtered = []
					for dev in devs:
						if re.search(hwid, dev.getAttribute('id')):
							if not filter:
								filtered.append(dev)
							else:
								(attr, method) = filter.split('.', 1)
								if dev.getAttribute(attr):
									if eval("dev.getAttribute(attr).%s" % method):
										filtered.append(dev)
								elif dev.hasChildNodes():
									for child in dev.childNodes:
										if (child.nodeName == attr) and child.hasChildNodes():
											if eval("child.firstChild.data.strip().%s" % method):
												filtered.append(dev)
												break
										try:
											if child.hasAttributes() and child.getAttribute(attr):
												if eval("child.getAttribute(attr).%s" % method):
													filtered.append(dev)
													break
										except Exception:
											pass
					devs = filtered

				logger.debug2("Found matching devices: %s", devs)
				devices.extend(devs)

			# Process matching xml nodes
			for i, device in enumerate(devices):
				if opsiClass not in opsiValues:
					opsiValues[opsiClass] = []
				opsiValues[opsiClass].append({})

				if not hwClass.get('Values'):
					break

				for attribute in hwClass['Values']:
					elements = [device]
					if not attribute.get('Opsi') or not attribute.get('Linux'):
						continue

					logger.debug2(u"Processing attribute '%s' : '%s'", attribute['Linux'], attribute['Opsi'])
					for attr in attribute['Linux'].split('||'):
						attr = attr.strip()
						method = None
						data = None
						for part in attr.split('/'):
							if '.' in part:
								(part, method) = part.split('.', 1)
							nextElements = []
							for element in elements:
								for child in element.childNodes:
									try:
										if child.nodeName == part:
											nextElements.append(child)
										elif child.hasAttributes() and (child.getAttribute('class') == part or child.getAttribute('id').split(':')[0] == part):
											nextElements.append(child)
									except Exception:
										pass
							if not nextElements:
								logger.warning(u"Attribute part '%s' not found", part)
								break
							elements = nextElements

						if not data:
							if not elements:
								opsiValues[opsiClass][i][attribute['Opsi']] = ''
								logger.warning(u"No data found for attribute '%s' : '%s'", attribute['Linux'], attribute['Opsi'])
								continue

							for element in elements:
								if element.getAttribute(attr):
									data = element.getAttribute(attr).strip()
								elif element.getAttribute('value'):
									data = element.getAttribute('value').strip()
								elif element.hasChildNodes():
									data = element.firstChild.data.strip()
						if method and data:
							try:
								logger.debug(u"Eval: %s.%s", data, method)
								data = eval("data.%s" % method)
							except Exception as e:
								logger.error(u"Failed to excecute '%s.%s': %s", data, method, e)
						logger.debug2(u"Data: %s", data)
						opsiValues[opsiClass][i][attribute['Opsi']] = data
						if data:
							break

		# Get hw info from dmidecode
		elif linuxClass.startswith('[dmidecode]'):
			opsiValues[opsiClass] = []
			for hwclass in linuxClass[11:].split('|'):
				(filterAttr, filterExp) = (None, None)
				if ':' in hwclass:
					(hwclass, filter) = hwclass.split(':', 1)
					if '.' in filter:
						(filterAttr, filterExp) = filter.split('.', 1)

				for dev in dmidecode.get(hwclass, []):
					if filterAttr and dev.get(filterAttr) and not eval("str(dev.get(filterAttr)).%s" % filterExp):
						continue
					device = {}
					for attribute in hwClass['Values']:
						if not attribute.get('Linux'):
							continue

						for aname in attribute['Linux'].split('||'):
							aname = aname.strip()
							method = None
							if '.' in aname:
								(aname, method) = aname.split('.', 1)
							if method:
								try:
									logger.debug(u"Eval: %s.%s", dev.get(aname, ''), method)
									device[attribute['Opsi']] = eval("dev.get(aname, '').%s" % method)
								except Exception as e:
									device[attribute['Opsi']] = u''
									logger.error(u"Failed to excecute '%s.%s': %s", dev.get(aname, ''), method, e)
							else:
								device[attribute['Opsi']] = dev.get(aname)
							if device[attribute['Opsi']]:
								break
					opsiValues[hwClass['Class']['Opsi']].append(device)

		# Get hw info from alsa hdaudio info
		elif linuxClass.startswith('[hdaudio]'):
			opsiValues[opsiClass] = []
			for (hdaudioId, dev) in hdaudio.items():
				device = {}
				for attribute in hwClass['Values']:
					if not attribute.get('Linux') or attribute['Linux'] not in dev:
						continue

					try:
						device[attribute['Opsi']] = dev[attribute['Linux']]
					except Exception as e:
						logger.warning(e)
						device[attribute['Opsi']] = u''
				opsiValues[opsiClass].append(device)

		# Get hw info from lsusb
		elif linuxClass.startswith('[lsusb]'):
			opsiValues[opsiClass] = []
			for (busId, dev) in lsusb.items():
				device = {}
				for attribute in hwClass['Values']:
					if not attribute.get('Linux'):
						continue

					try:
						value = pycopy.deepcopy(dev)
						for key in attribute['Linux'].split('/'):
							method = None
							if '.' in key:
								(key, method) = key.split('.', 1)
							if not isinstance(value, dict) or key not in value:
								logger.error(u"Key '%s' not found", key)
								value = u''
								break
							value = value[key]
							if isinstance(value, list):
								value = u', '.join(value)
							if method:
								value = eval("value.%s" % method)

						device[attribute['Opsi']] = value
					except Exception as e:
						logger.warning(e)
						device[attribute['Opsi']] = u''
				opsiValues[opsiClass].append(device)

	opsiValues['SCANPROPERTIES'] = [{"scantime": time.strftime("%Y-%m-%d %H:%M:%S")}]
	logger.debug(u"Result of hardware inventory:\n" + objectToBeautifiedText(opsiValues))
	return opsiValues
