#
# ***** BEGIN LICENSE BLOCK *****
# Zimbra Collaboration Suite Server
# Copyright (C) 2010, 2011, 2012, 2013, 2014, 2015, 2016 Synacor, Inc.
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


from logmsg import *
import shlex
import subprocess
import time
import StringIO

from com.zimbra.cs.account import Provisioning
from com.zimbra.cs.account.ldap import LdapProvisioning
from com.zimbra.common.localconfig import LC
from com.zimbra.cs.extension import ExtensionDispatcherServlet
from com.zimbra.cs.httpclient import URLUtil
from com.zimbra.cs.util import ProxyConfGen

exe = {
	"POSTCONF"      : "bin/postconf -e",
	"POSTCONFD"     : "bin/postconf -X",
	"ZMPROV"        : "bin/zmprov -l",
	"ZMLOCALCONFIG" : "bin/zmlocalconfig",
	'PROXY'         : "bin/zmproxyctl",
	'STATS'         : "bin/zmstatctl",
	'ARCHIVING'     : "bin/zmamavisdctl",
	'MEMCACHED'     : "bin/zmmemcachedctl",
	'MTA'           : "bin/zmmtactl",
	'ANTISPAM'      : "bin/zmantispamctl",
	'AMAVIS'        : "bin/zmamavisdctl",
	'ANTIVIRUS'     : "bin/zmclamdctl",
	'SASL'          : "bin/zmsaslauthdctl",
	'MAILBOXD'      : "bin/zmmailboxdctl",
	'ZIMBRA'        : "bin/zmmailboxdctl",
	'ZIMBRAADMIN'   : "bin/zmmailboxdctl",
	'SERVICE'       : "bin/zmmailboxdctl",
	'ZIMLET'        : "bin/zmmailboxdctl",
	'SPELL'         : "bin/zmspellctl",
	'LDAP'          : "bin/ldap",
	'SNMP'          : "bin/zmswatchctl",
	'LOGGER'        : "bin/zmloggerctl",
	'MAILBOX'       : "bin/zmstorectl",
	'CBPOLICYD'     : "bin/zmcbpolicydctl",
	'PROXYGEN'      : "libexec/zmproxyconfgen",
	'CONVERTD'      : "bin/zmconvertctl",
	'OPENDKIM'	: "bin/zmopendkimctl",
	'DNSCACHE'	: "bin/zmdnscachectl",
	}

provisioning = Provisioning.getInstance(Provisioning.CacheMode.OFF)

class Command:
	P = provisioning

	@classmethod
	def resetProvisioning(cls, type):
		if type == "local":
			LC.reload()
		else:
			try:
				cls.P.flushCache(Provisioning.CacheEntryType.fromString(type), None)
			except:
				pass  # mailboxd is down, or not running here, either way we don't care.

	def __init__(self, desc, name, cmd=None, func=None, args=None, base="/opt/zimbra"):
		self.desc = desc
		self.name = name
		self.cmd = None
		if cmd:
			self.cmd = '/'.join((base,cmd))
		self.func = func
		self.args = args
		self.resetState()
	
	def __str__(self):
		if self.cmd:
			return "%s %s %s %s" % (self.name, self.cmd, self.status, self.error)
		else:
			return "%s %s(%s) %s %s" % (self.name, self.func, self.args, self.status, self.error)

	def resetState(self):
		self.status = None
		self.output = None
		self.error = None

	def execute(self,a=None):
		Log.logMsg(5,"Executing: %s" % (str(self),))
		self.resetState
		self.lastChecked = time.clock()

		output = error = ""
		t1 = time.clock()
		st = ""
		if self.cmd:
			cm = self.cmd
			st = cm
			(rc, output, error) = self.runCmd(a)
			if a:
				st = cm % a
		else:
			cm = self.func
			st = cm
			(rc, output, error) = cm(self.args, a)

		dt = time.clock() - t1
		self.status = rc
		if (rc < 0):
			self.error = "UNKNOWN: %s died with signal %s " % (self.name,rc)
			Log.logMsg(2, self.error)
			raise Exception, self.error
		else:
			if (not output):
				output = "UNKNOWN OUTPUT"
			if (not error):
				if rc == 0:
					error = "OK"
				else:
					error = "UNKNOWN ERROR"

			self.output = output
			self.error = error
			if rc:
				Log.logMsg(4, "Executed: %s returned %d (%d - %d) (%.2f sec): output='%s'" % (st, rc, len(output), len(error), dt, output))
			else:
				Log.logMsg(4, "Executed: %s returned %d (%d - %d) (%.2f sec)" % (st, rc, len(output), len(error), dt))

		return rc

	def runCmd(self, a=None):
		if (a):
			cmd = self.cmd % a
		else:
			cmd = self.cmd
		args = shlex.split(cmd)
		Log.logMsg(4, "Executing %s" % (cmd,))
		p = subprocess.Popen(args, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

		rc = output = error = None
		while rc is None:
			(output, error) = p.communicate()
			rc = p.wait()

		Log.logMsg(4, "runCmd: cmd='%s', args='%s', rc='%s', output='%s', error='%s'" % (
			cmd, args, rc, output, error))
		return (rc, output, error)

	def runFunc(self, a=None):
		if (a):
			return self.func(a)
		else:
			return self.func()

def gamau(sArgs=None, aArgs=None):
	output = error = ""
	rc = 0

	try:
		P = Command.P
		o = []
		for server in P.getAllServers():
			if server.getBooleanAttr(Provisioning.A_zimbraMtaAuthTarget, False):
				o.append(URLUtil.getMtaAuthURL(server))

		output = o

	except:
		rc = 1
		error = str(sys.exc_info()[1])
	return (rc, output, error)

def garpu(sArgs=None, aArgs=None):
	output = error = ""
	rc = 0

	try:
		P = Command.P
		o = []
		REVERSE_PROXY_PROTO = ""
		REVERSE_PROXY_PORT = 7072
		REVERSE_PROXY_PATH = ExtensionDispatcherServlet.EXTENSION_PATH + "/nginx-lookup"
		for server in P.getAllMailClientServers():
			if server.getBooleanAttr(Provisioning.A_zimbraReverseProxyLookupTarget, False):
				o.append("%s%s:%d%s" % (REVERSE_PROXY_PROTO, server.getAttr(Provisioning.A_zimbraServiceHostname, ""),REVERSE_PROXY_PORT,REVERSE_PROXY_PATH))

		output = o

	except:
		rc = 1
		error = str(sys.exc_info()[1])
	return (rc, output, error)

def garpb(sArgs=None, aArgs=None):
	output = error = ""
	rc = 0

	try:
		P = Command.P
		o = []
		REVERSE_PROXY_PROTO = ""
		for server in P.getAllServers():
			isTarget = server.getBooleanAttr(Provisioning.A_zimbraReverseProxyLookupTarget, False)
			if not isTarget:
				continue
			mode = server.getAttr(Provisioning.A_zimbraMailMode, None)
			if mode is None:
				continue
			if Provisioning.MailMode.fromString(mode) in \
				(Provisioning.MailMode.http, Provisioning.MailMode.mixed, Provisioning.MailMode.both):
			     backendPort = server.getIntAttr(Provisioning.A_zimbraMailPort, 0)
			else:
			     backendPort = server.getIntAttr(Provisioning.A_zimbraMailSSLPort, 0)
			serviceName = server.getAttr(Provisioning.A_zimbraServiceHostname, "")
			o.append("%s%s:%d" % (REVERSE_PROXY_PROTO, serviceName, backendPort))

		# I think this is a hack for the old version of zmconfigd
		output = o
		if not len(o):
			output = ["    server localhost:8080;"]

	except:
		rc = 1
		error = str(sys.exc_info()[1])

	return (rc, output, error)

def gamcs(sArgs=None, aArgs=None):
	output = error = ""
	rc = 0

	try:
		# Looks like we get ldap by default,
		# unless we create an instance and call setInstance ourselves
		P = Command.P
		o = []
		for server in P.getAllServers(Provisioning.SERVICE_MEMCACHED):
			o.append("%s:%s" % (server.getAttr(Provisioning.A_zimbraServiceHostname, ""),server.getAttr(Provisioning.A_zimbraMemcachedBindPort, "")))

		output = o

	except:
		rc = 1
		error = str(sys.exc_info()[1])
	return (rc, output, error)

def getserver(sArgs=None, aArgs=None):
	output = error = ""
	rc = 0

	try:
		# Looks like we get ldap by default,
		# unless we create an instance and call setInstance ourselves
		P = Command.P
		output = P.getLocalServer().getAttrs(True).entrySet()

	except:
		rc = 1
		error = str(sys.exc_info()[1])
	return (rc, output, error)

def getglobal(sArgs=None, aArgs=None):
	output = error = ""
	rc = 0

	try:
		# Looks like we get ldap by default,
		# unless we create an instance and call setInstance ourselves
		P = Command.P
		output = P.getConfig().getAttrs(True).entrySet()

	except:
		rc = 1
		error = str(sys.exc_info()[1])
	return (rc, output, error)

def getlocal(sArgs=None, rArgs=None):
	output = error = ""
	rc = 0
	try:
		output = [(key, LC.get(key)) for key in sorted(LC.getAllKeys())]
		#output = '\n'.join(["%s = %s" % (key, LC.get(key)) for key in sorted(LC.getAllKeys())])
	except Exception, e:
		rc = 1
		error = str(e)
	return (rc, output, error)

def proxygen(sArgs=None, rArgs=None):
	Log.logMsg(5, "proxygen: sArgs='%s', rArgs='%s'" % (sArgs, rArgs))
	rc = ProxyConfGen.createConf(["-s",rArgs[0]])
	return (rc, "", "")

commands = {
	"gs:enabled" : Command(
		desc = "Enabled Services for host",
		name = "gs:enabled",
		cmd  = exe['ZMPROV']+" gs %s zimbraServiceEnabled",
	),
	"gs" : Command(
		desc = "Configuration for server ",
		name = "gs",
		# cmd  = exe['ZMPROV']+" gs %s",
		func = getserver,
	),
	"localconfig" : Command(
		desc = "Local server configuration",
		name = "localconfig",
		func  = getlocal,
		# cmd  = exe["ZMLOCALCONFIG"]+" -s -x",
	),
	"gacf" : Command(
		desc = "Global system configuration",
		name = "gacf",
		func  = getglobal,
		# cmd  = exe["ZMPROV"]+" gacf",
	),
	"gamau" : Command(
		desc = "All MTA Authentication Target URLs",
		name = "getAllMtaAuthURLs",
		func = gamau,
		# cmd  = exe["ZMPROV"]+" gamau",
	),
	"garpu" : Command(
		desc = "All Reverse Proxy URLs",
		name = "getAllReverseProxyURLs",
		func = garpu,
		# cmd  = exe["ZMPROV"]+" garpu",
	),
	"garpb" : Command(
		desc = "All Reverse Proxy Backends",
		name = "getAllReverseProxyBackends",
		func = garpb,
		# cmd  = exe["ZMPROV"]+" garpb",
	),
	"gamcs" : Command(
		desc = "All Memcached Servers",
		name = "getAllMemcachedServers",
		func = gamcs,
		# cmd  = exe["ZMPROV"]+" gamcs",
	),
	"postconf" : Command(
		desc = "postconf",
		name = "postconf",
		cmd  = exe["POSTCONF"] + " %s",
		# cmd  = exe["POSTCONF"] + " %s='%s'",
	),
	"postconfd" : Command(
		desc = "postconfd",
		name = "postconfd",
		cmd  = exe["POSTCONFD"] + " %s",
		# cmd  = exe["POSTCONFD"] + " %s='%s'",
	),
	"proxygen" : Command(
		desc = "proxygen",
		name = "proxygen",
		func = proxygen,
	),
	"proxy" : Command(
		desc = "proxy",
		name = "proxy",
		cmd  = exe["PROXY"] + " %s",
	),
	"stats" : Command(
		desc = "stats",
		name = "stats",
		cmd  = exe["STATS"] + " %s",
	),
	"archiving" : Command(
		desc = "archiving",
		name = "archiving",
		cmd  = exe["ARCHIVING"] + " %s",
	),
	"memcached" : Command(
		desc = "memcached",
		name = "memcached",
		cmd  = exe["MEMCACHED"] + " %s",
	),
	"mta" : Command(
		desc = "mta",
		name = "mta",
		cmd  = exe["MTA"] + " %s",
	),
	"antispam" : Command(
		desc = "antispam",
		name = "antispam",
		cmd  = exe["ANTISPAM"] + " %s",
	),
	"antivirus" : Command(
		desc = "antivirus",
		name = "antivirus",
		cmd  = exe["ANTIVIRUS"] + " %s",
	),
	"amavis" : Command(
		desc = "amavis",
		name = "amavis",
		cmd  = exe["AMAVIS"] + " %s",
	),
	"opendkim" : Command(
		desc = "opendkim",
		name = "opendkim",
		cmd  = exe["OPENDKIM"] + " %s",
	),
	"dnscache" : Command(
		desc = "dnscache",
		name = "dnscache",
		cmd  = exe["DNSCACHE"] + " %s",
	),
	"cbpolicyd" : Command(
		desc = "cbpolicyd",
		name = "cbpolicyd",
		cmd  = exe["CBPOLICYD"] + " %s",
	),
	"sasl" : Command(
		desc = "sasl",
		name = "sasl",
		cmd  = exe["SASL"] + " %s",
	),
	"mailboxd" : Command(
		desc = "mailboxd",
		name = "mailboxd",
		cmd  = exe["MAILBOXD"] + " %s",
	),
	"zimbra" : Command(
		desc = "zimbra",
		name = "zimbra",
		cmd  = exe["ZIMBRA"] + " %s",
		),
	"zimbraadmin" : Command(
		desc = "zimbraadmin",
		name = "zimbraadmin",
		cmd  = exe["ZIMBRAADMIN"] + " %s",
	),
	"service" : Command(
		desc = "service",
		name = "service",
		cmd  = exe["SERVICE"] + " %s",
	),
	"zimlet" : Command(
		desc = "zimlet",
		name = "zimlet",
		cmd  = exe["ZIMLET"] + " %s",
	),
	"spell" : Command(
		desc = "spell",
		name = "spell",
		cmd  = exe["SPELL"] + " %s",
	),
	"ldap" : Command(
		desc = "ldap",
		name = "ldap",
		cmd  = exe["LDAP"] + " %s",
	),
	"snmp" : Command(
		desc = "snmp",
		name = "snmp",
		cmd  = exe["SNMP"] + " %s",
	),
	"logger" : Command(
		desc = "logger",
		name = "logger",
		cmd  = exe["LOGGER"] + " %s",
	),
	"mailbox" : Command(
		desc = "mailbox",
		name = "mailbox",
		cmd  = exe["MAILBOX"] + " %s",
	),
	"convertd" : Command(
		desc = "convertd",
		name = "convertd",
		cmd  = exe["CONVERTD"] + " %s",
	),
	}

miscCommands = ["garpu","garpb","gamcs","gamau"]
