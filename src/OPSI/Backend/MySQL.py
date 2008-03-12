# -*- coding: utf-8 -*-
"""
   ========================================
   =          OPSI MySQL Module           =
   ========================================
   
   @copyright:	uib - http://www.uib.de - <info@uib.de>
   @author: Patrick Ohler <p.ohler@uib.de>, Jan Schneider <j.schneider@uib.de>
   @license: GNU GPL, see COPYING for details.
"""

__version__ = '0.1'

# Imports
import MySQLdb, warnings, time
from _mysql_exceptions import *

# OPSI imports
from OPSI.Backend.Backend import *
from OPSI.Logger import *

# Get logger instance
logger = Logger()


# ======================================================================================================
# =                                       CLASS MYSQL                                                  =
# ======================================================================================================

class MySQL:
	def __init__(self, username = 'root', password = '', address = 'localhost', database = 'opsi'):
		self.__conn__ = None
		try:
			self.__conn__ = MySQLdb.connect(
							host = address,
							user = username,
							passwd = password,
							db = database )
		except Exception, e:
			raise BackendIOError("Failed to connect to database '%s' address '%s': %s" % (database, address, e))
		
		self.__cursor__ = self.__conn__.cursor(MySQLdb.cursors.DictCursor)
		
	def db_query(self, query):
		self.__cursor__.execute(query)
		return self.__cursor__.rowcount
		
	def db_getSet(self, query):
		self.__cursor__.execute(query)
		valueSet = self.__cursor__.fetchall()
		if not valueSet:
			logger.debug("No result for query '%s'" % query)
			return []
		return valueSet
		
	def db_getRow(self, query):
		self.__cursor__.execute(query)
		row = self.__cursor__.fetchone()
		if not row:
			logger.debug("No result for query '%s'" % query)
			return {}
		logger.debug2("Result: '%s'" % row)
		return row
		
	def db_insert(self, table, valueHash):
		colNames = values = ''
		for (key, value) in valueHash.items():
			colNames += "`%s`, " % key
			if type(value) is type(''):
				# String-value
				values += "\'%s\', " % value.replace("'", "\\\'")
			else:
				values += "%s, " % value
		logger.debug("INSERT INTO `%s` (%s) VALUES (%s);" % (table, colNames[:-2], values[:-2]))
		self.__cursor__.execute("INSERT INTO `%s` (%s) VALUES (%s);" % (table, colNames[:-2], values[:-2]))
		return self.__cursor__.lastrowid
		#return self.__cursor__.rowcount
		
	#def db_update(self, table, valueHash):
	#	pass
	
	def db_info(self):
		return self.__conn__.info()
	
	def db_warning_count(self):
		return self.__conn__.warning_count()
		
	def db_close(self):
		self.__cursor__.close()
		self.__conn__.commit()
		self.__conn__.close()

# ======================================================================================================
# =                                    CLASS MYSQLBACKEND                                              =
# ======================================================================================================
class MySQLBackend(DataBackend):
	
	def __init__(self, username = '', password = '', address = 'localhost', backendManager=None, args={}):
		''' MySQLBackend constructor. '''
		
		self._backendManager = backendManager
		
		# Default values
		self._defaultDomain = 'opsi.org'
		self._username = username
		self._password = password
		self._address = address
		self._database = 'opsi'
		
		# Parse arguments
		for (option, value) in args.items():
			if   (option.lower() == 'database'):		self._database = value
			elif (option.lower() == 'defaultdomain'): 	self._defaultDomain = value
			elif (option.lower() == 'host'):		self._address = value
			elif (option.lower() == 'username'):		self._username = value
			elif (option.lower() == 'password'):		self._password = value
			else:
				logger.warning("Unknown argument '%s' passed to FileBackend constructor" % option)
		
		warnings.showwarning = self._showwarning
		self.__mysql__ = MySQL(username = self._username, password = self._password, address = self._address, database = self._database)
		 
		
	def _showwarning(self, message, category, filename, lineno, file=None):
		#logger.warning("%s (file: %s, line: %s)" % (message, filename, lineno))
		logger.warning(message)
	
	#def _getRulesFromFile_(self, RulesFile):
	#	general = relationalTable = additionalHardwareCols = ''
	#	
	#	f = open(RulesFile, 'r')
	#	section = ''
	#	for line in f.readlines():
	#		line2 = line.strip()
	#		if not line2 or line2[0] in ('#', '/', ';'):
	#			continue
	#		
	#		if re.match('\[(\w+)\]', line):
	#			match = re.search('\[(\w+)\]', line)
	#			section = match.group(1)
	#			continue
	#		
	#		if section and line:
	#			if section=='additionalHardwareCols':
	#				additionalHardwareCols += line.strip() + '\n'
	#			elif section=='general':
	#				general += line.strip() + '\n'
	#			elif section=='relationalTable':
	#				relationalTable += line.strip() + '\n'
	#	f.close()
	#	
	#	return {
	#		"additionalHardwareCols": additionalHardwareCols,
	#		"general": general,
	#		"relationalTable": relationalTable }
		
	#def _toSQL_(self, classes, rules):
	#	'''
	#	example:
	#	CREATE TABLE `test` (
	#		`id` INT NOT NULL ,
	#		`text` VARCHAR( 255 ) NOT NULL ,
	#		`time` TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ,
	#		PRIMARY KEY ( `id` )
	#	) ENGINE = MYISAM ;
	#	'''
	#	
	#	text = ''
	#	for className in classes:
	#		hardwareTable = relationalTable = ''
	#		hardwareTable += 'CREATE TABLE `%s` (\n' % (className["Class"]["Opsi"])
	#		hardwareTable += rules["additionalHardwareCols"]
	#		
	#		relationalTable += 'CREATE TABLE `PC2%s` (\n' % (className["Class"]["Opsi"])
	#		relationalTable += rules["relationalTable"]
	#		
	#		for item in className["Values"]:
	#			if item["Scope"]=="g":
	#				hardwareTable += '`%s` %s NULL,\n' % (item["Opsi"], item["Type"])
	#			elif item["Scope"]=="i":
	#				relationalTable += '`%s` %s NULL,\n' % (item["Opsi"], item["Type"])
	#		if hardwareTable.strip()[-1:]==',':
	#			hardwareTable = hardwareTable.strip()[:-1]+'\n'
	#		if relationalTable.strip()[-1:]==',':
	#			relationalTable = relationalTable.strip()[:-1]+'\n'
	#		
	#		text += hardwareTable + ') ENGINE = MYISAM ;\n\n' + relationalTable + ') ENGINE = MYISAM ;\n\n'
	#	
	#	text += rules["general"]	
	#	return text
	
	def _writeToServer_(self, queries):
		for query in queries.split(';'):
			if query.strip():
				self.__mysql__.db_query(query + ' ;')
	
	def createOpsiBase(self):
		logger.notice('Creating opsi base')
		
		logger.debug('Creating table HOST')
		self._writeToServer_('CREATE TABLE HOST (host_id INT NOT NULL AUTO_INCREMENT, hostId varchar(50) NOT NULL, PRIMARY KEY(`host_id`) ) ENGINE = MYISAM;')
		
		opsiHWAuditConf = self.getOpsiHWAuditConf()
		for config in opsiHWAuditConf:
			hwClass = config['Class']['Opsi']
			logger.debug("Processing hardware class '%s'" % hwClass)
			
			hardwareTable  =  'CREATE TABLE `HARDWARE_DEVICE_' + hwClass + '` (\n' + \
						'`hardware_id` INT NOT NULL AUTO_INCREMENT,\n' + \
						'PRIMARY KEY( `hardware_id` ),\n'
			
			relationalTable = 'CREATE TABLE `HARDWARE_CONFIG_' + hwClass + '` (\n' + \
						'`config_id` INT NOT NULL AUTO_INCREMENT,\n' + \
						'PRIMARY KEY( `config_id` ),\n' + \
						'`host_id` INT NOT NULL,\n' + \
						'`hardware_id` INT NOT NULL,\n' + \
						'`audit_firstseen` TIMESTAMP NOT NULL DEFAULT \'0000-00-00 00:00:00\',\n' + \
						'`audit_lastseen` TIMESTAMP NOT NULL DEFAULT \'0000-00-00 00:00:00\',\n' + \
						'`audit_state` TINYINT NOT NULL,\n'
			for value in config['Values']:
				logger.debug("  Processing value '%s'" % value['Opsi'])
				if   (value['Scope'] == 'g'):
					hardwareTable  +=  '`%s` %s NULL,\n' % (value['Opsi'], value["Type"])
				elif (value['Scope'] == 'i'):
					relationalTable += '`%s` %s NULL,\n' % (value['Opsi'], value["Type"])
			
			hardwareTable = hardwareTable.strip()
			relationalTable = relationalTable.strip()
			if (hardwareTable[-1] == ','):
				hardwareTable = hardwareTable[:-1] + '\n) ENGINE = MYISAM ;\n'
			if (relationalTable[-1] == ','):
				relationalTable = relationalTable[:-1] + '\n) ENGINE = MYISAM ;\n'
			
			logger.debug(hardwareTable)
			logger.debug(relationalTable)
			
			self._writeToServer_(hardwareTable)
			self._writeToServer_(relationalTable)
		
	def getHardwareInformation_listOfHashes(self, hostId):
		return []
	
	def getHardwareInformation_hash(self, hostId):
		info = {}
		hostDbId = self.__mysql__.db_getRow("SELECT `host_id` FROM `HOST` WHERE `hostId`='%s'" % hostId).get('host_id')
		if not hostDbId:
			logger.warning("No hardware information found for host '%s'" % hostId)
			return info
		
		newest = time.strptime("2000-01-01 00:00:00", "%Y-%m-%d %H:%M:%S")
		opsiHWAuditConf = self.getOpsiHWAuditConf()
		for config in opsiHWAuditConf:
			hwClass = config['Class']['Opsi']
			devices = []
			for hwConfig in self.__mysql__.db_getSet("SELECT * FROM `HARDWARE_CONFIG_%s` WHERE `audit_state`=1 AND `host_id`=%s" \
									% (hwClass, hostDbId)):
				device = {}
				logger.debug2("Host to hardware class '%s': %s" % (hwClass, hwConfig))
				hardware = self.__mysql__.db_getRow("SELECT * FROM `HARDWARE_DEVICE_%s` WHERE `hardware_id`='%s'" % (hwClass, hwConfig['hardware_id']))
				logger.debug2("Hardware class '%s': %s" % (hwClass, hardware))
				for (key, value) in hardware.items():
					if key in ('hardware_id'):
						continue
					if (value == None):
						value = ""
					device[key] = value
				for (key, value) in hwConfig.items():
					if key in ('config_id', 'hardware_id', 'host_id', 'audit_firstseen', 'audit_state'):
						continue
					if (key == 'audit_lastseen'):
						lastseen = time.strptime(str(value), "%Y-%m-%d %H:%M:%S")
						if (newest < lastseen):
							newest = lastseen
						continue
					if (value == None):
						value = ""
					device[key] = value
				if device:
					devices.append(device)
			if devices:
				info[hwClass] = devices
		
		info['SCANPROPERTIES'] = [ {'scantime': time.strftime("%Y-%m-%d %H:%M:%S", newest) } ]
		return info
	
	def setHardwareInformation(self, hostId, info):
		if not type(info) is dict:
			raise BackendBadValueError("Hardware information must be dict")
		
		'''
		INSERT INTO `test` ( `test1` , `test2` , `test3` , `test4` )
			VALUES (
			'test', '23', NOW( ) , '0000-00-00 00:00:00'
			);
		'''
		now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
		
		# Is the host already in the db? if yes, wich id?
		hostDbId = self.__mysql__.db_getRow("SELECT host_id FROM HOST WHERE hostId='%s'" % hostId)
		
		if hostDbId:
			hostDbId = hostDbId['host_id']
		else:
			hostDbId = self.__mysql__.db_insert( "HOST", { "hostId": hostId } )
		
		config = self.getOpsiHWAuditConf()
		# Reorganize the config quickly
		configNew = {}
		for i in config:
			for j in i['Values']:
				if not configNew.has_key(i['Class']['Opsi']):
					configNew[i['Class']['Opsi']] = {}
				configNew[i['Class']['Opsi']][j['Opsi']] = j['Scope']
		
		#logger.debug2( jsonObjToBeautifiedText(configNew) )
		queries = ''
		for (hwClass, values) in info.items():
			if (hwClass == 'SCANPROPERTIES'):
				continue
			
			configIdsSeen = []
			
			for value in values:
				individual = {}
				hardware = {}
				for (opsiName, opsiValue) in value.items():
					if (type(opsiValue) == type(None)):
						continue
					if (configNew[hwClass][opsiName] == 'i'):
						# this is an individual information, put it into the ralational table
						if type(opsiValue) is unicode:
							individual[opsiName] = opsiValue.encode('utf-8')
						else:
							individual[opsiName] = opsiValue
					else:
						# this musst be an global hardware information, put it into the hardware table
						if type(opsiValue) is unicode:
							hardware[opsiName] = opsiValue.encode('utf-8')
						else:
							hardware[opsiName] = opsiValue
				
				# Hardware
				hwId = -1
				query = 'SELECT `hardware_id` FROM `HARDWARE_DEVICE_%s` WHERE' % hwClass
				for (k, v) in hardware.items():
					if type(v) is type(''):
						# String-value
						query += " `%s` = '%s' AND" % (k, v.replace("'", "\\\'"))
					else:
						query += " `%s` = %s AND" % (k, v)
				query = query[:-4] + ';'
				#logger.debug2("Query: %s" % query)
				current = self.__mysql__.db_getSet(query)
				if (len(current) >= 1):
					# Hardware device already exists in database
					logger.debug("Hardware device already in database")
					if (len(current) > 1):
						# Hardware device exists more than once
						hwIds = []
						for c in current:
							hwIds.append(str(c['hardware_id']))
						logger.warning("Redundant entries in hardware database: table 'HARDWARE_DEVICE_%s', hardware_ids: %s" \
									% (hwClass, ', '.join(hwIds)) )
					hwId = current[0]['hardware_id']
				else:
					logger.debug("Adding hardware device to database")
					hwId = self.__mysql__.db_insert('HARDWARE_DEVICE_' + hwClass, hardware)
				
				# Individual
				individual["hardware_id"] = hwId
				individual["host_id"] = hostDbId
				individual["audit_firstseen"] = now
				individual["audit_lastseen"] = now
				individual["audit_state"] = 1
				confId = -1
				query = 'SELECT `config_id` FROM `HARDWARE_CONFIG_%s` WHERE' % hwClass
				for (k, v) in individual.items():
					if k in ('audit_firstseen', 'audit_lastseen', 'audit_state'):
						continue
					if type(v) is type(''):
						# String-value
						query += " `%s` = '%s' AND" % (k, v.replace("'", "\\\'"))
					else:
						query += " `%s` = %s AND" % (k, v)
				query = query + " `audit_lastseen` != '%s'" % now
				logger.debug2("Query: %s" % query)
				current = self.__mysql__.db_getSet(query)
				if (len(current) >= 1):
					# Host specific hardware config already exists in database
					logger.debug("Host specific hardware config already in database")
					if (len(current) > 1):
						# Host specific hardware config exists more than once
						confIds = []
						for c in current:
							confIds.append(str(c['config_id']))
						logger.warning("Redundant entries in hardware database: table 'HARDWARE_CONFIG_%s', config_ids: %s" \
									% (hwClass, ', '.join(confIds)) )
					confId = current[0]['config_id']
					self.__mysql__.db_query("UPDATE `HARDWARE_CONFIG_%s` SET `audit_lastseen` = '%s' WHERE `config_id` = %d;" % (hwClass, now, confId))
				else:
					logger.debug("Adding host specific hardware config to database")
					confId = self.__mysql__.db_insert("HARDWARE_CONFIG_%s" % hwClass, individual)
				configIdsSeen.append(confId)
			
			for config in self.__mysql__.db_getSet('SELECT `config_id` FROM `HARDWARE_CONFIG_%s` WHERE `host_id`=%d;' % (hwClass, hostDbId)):
				if config['config_id'] not in configIdsSeen:
					logger.info("Hardware config with config_id %d vanished (table HARDWARE_CONFIG_%s), updating audit_state" \
								% (config['config_id'], hwClass))
					self.__mysql__.db_query("UPDATE `HARDWARE_CONFIG_%s` SET `audit_state` = 0 WHERE `config_id` = %d;" % (hwClass, confId))
	
	def deleteHardwareInformation(self, hostId):
		pass
	
	def exit(self):
		self.__mysql__.db_close()





