#
# ***** BEGIN LICENSE BLOCK *****
# Zimbra Collaboration Suite Server
# Copyright (C) 2010, 2012, 2013, 2014, 2015, 2016 Synacor, Inc.
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software Foundation,
# version 2 of the License.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program.
# If not, see <https://www.gnu.org/licenses/>.
# ***** END LICENSE BLOCK *****
#

import os
import conf
import time
import re
from org.apache.log4j import Logger, MDC

class Log:
	prefix = ("zmconfigd[%d]" % os.getpid())
	mylog = Logger.getLogger(prefix);
	MDC.put("PID", os.getpid());

	@classmethod
	def initLogging(cls, c = None):
		if c:
			cls.cf = c
			if cls.cf.loglevel > 5:
				cls.cf.loglevel = 5
		else:
			cls.cf = conf.Config()

	@classmethod
	def logMsg(cls, lvl, msg):

		if lvl > 5:
			lvl = 5
		msg = re.sub(r"\s|\n", " ", msg)

		if lvl == 0:
			Log.mylog.fatal(msg)
			Log.mylog.warn(2, "%s: shutting down" % (cls.cf.progname,) )
			os._exit(1)
		elif lvl == 1:
			Log.mylog.error(msg)
		elif lvl == 2:
			Log.mylog.warn(msg)
		elif lvl == 3:
			Log.mylog.info(msg)
		elif lvl == 4:
			Log.mylog.debug(msg)
		else:
			Log.mylog.trace(msg)

Log.initLogging()
