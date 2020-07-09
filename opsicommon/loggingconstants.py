import logging

DEFAULT_COLORED_FORMAT = "%(log_color)s[%(opsilevel)d] [%(asctime)s.%(msecs)03d]%(reset)s [%(contextstring)s] %(message)s   (%(filename)s:%(lineno)d)"
DEFAULT_FORMAT = "[%(opsilevel)d] [%(asctime)s.%(msecs)03d] [%(contextstring)s] %(message)s   (%(filename)s:%(lineno)d)"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
CONTEXT_STRING_MIN_LENGTH = 32

LOG_COLORS = {
	'SECRET': 'thin_yellow',
	'TRACE': 'thin_white',
	'DEBUG': 'white',
	'INFO': 'bold_white',
	'NOTICE': 'bold_green',
	'WARNING': 'bold_yellow',
	'ERROR': 'red',
	'CRITICAL': 'bold_red',
	'ESSENTIAL': 'bold_cyan'
}
SECRET_REPLACEMENT_STRING = '***secret***'

logging.NONE = 0
logging.NOTSET = logging.NONE
logging.SECRET = 10
logging.CONFIDENTIAL = logging.SECRET
logging.TRACE = 20
logging.DEBUG2 = logging.TRACE
logging.DEBUG = 30
logging.INFO = 40
logging.NOTICE = 50
logging.WARNING = 60
logging.WARN = logging.WARNING
logging.ERROR = 70
logging.CRITICAL = 80
logging.ESSENTIAL = 90
logging.COMMENT = logging.ESSENTIAL

logging._levelToName = {
	logging.SECRET: 'SECRET',
	logging.TRACE: 'TRACE',
	logging.DEBUG: 'DEBUG',
	logging.INFO: 'INFO',
	logging.NOTICE: 'NOTICE',
	logging.WARNING: 'WARNING',
	logging.ERROR: 'ERROR',
	logging.CRITICAL: 'CRITICAL',
	logging.ESSENTIAL: 'ESSENTIAL',
	logging.NONE: 'NONE'
}

logging._nameToLevel = {
	'SECRET': logging.SECRET,
	'TRACE': logging.TRACE,
	'DEBUG': logging.DEBUG,
	'INFO': logging.INFO,
	'NOTICE': logging.NOTICE,
	'WARNING': logging.WARNING,
	'ERROR': logging.ERROR,
	'CRITICAL': logging.CRITICAL,
	'ESSENTIAL': logging.ESSENTIAL,
	'NONE': logging.NONE
}

logging._levelToOpsiLevel = {
	logging.SECRET: 9,
	logging.TRACE: 8,
	logging.DEBUG: 7,
	logging.INFO: 6,
	logging.NOTICE: 5,
	logging.WARNING: 4,
	logging.ERROR: 3,
	logging.CRITICAL: 2,
	logging.ESSENTIAL: 1,
	logging.NONE: 0
}

logging._opsiLevelToLevel = {
	9: logging.SECRET,
	8: logging.TRACE,
	7: logging.DEBUG,
	6: logging.INFO,
	5: logging.NOTICE,
	4: logging.WARNING,
	3: logging.ERROR,
	2: logging.CRITICAL,
	1: logging.ESSENTIAL,
	0: logging.NONE
}

LOG_SECRET    = logging.SECRET
LOG_TRACE     = logging.TRACE
LOG_DEBUG     = logging.DEBUG
LOG_INFO      = logging.INFO
LOG_NOTICE    = logging.NOTICE
LOG_WARNING   = logging.WARNING
LOG_ERROR     = logging.ERROR
LOG_CRITICAL  = logging.ESSENTIAL
LOG_ESSENTIAL = logging.ESSENTIAL
LOG_NONE      = logging.NONE
