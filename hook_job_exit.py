#!/usr/bin/python

import socket
import pickle
import sys
import syslog
import os
from amqp_common import *

# Open a connection to the system logger
syslog.openlog (os.path.basename(sys.argv[0]))

try:
   try:
      config = read_config_file("AMQP_Module")
   except config_err, error:
      raise exception_handler(syslog.LOG_ERR, *(error.msg + ("Exiting.","")))

   # Create an exit message
   msg = condor_wf()
   exit_status = sys.argv[1]
   if exit_status == "exit":
      msg.type = condor_wf_types.exit_exit
   elif exit_status == "remove":
      msg.type = condor_wf_types.exit_remove
   elif exit_status == "hold":
      msg.type = condor_wf_types.exit_hold
   elif exit_status == "evict":
      msg.type = condor_wf_types.exit_evict
   else:
      print "Unknown exit status received"

   # Store the ClassAd from STDIN in the data portion of the message
   cwd = os.getcwd()
   msg.data = ""
   for line in sys.stdin:
      msg.data = msg.data + str(line)
   msg.data = msg.data + "OriginatingCWD = \"" + cwd + "\"\n"

   # Send the message
   client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   client_socket.connect((config['ip'], int(config['port'])))
   client_socket.send(pickle.dumps(msg, 2))

   # Get acknowledgement that the exit work has completed
   reply = socket_read_all(client_socket)
   client_socket.shutdown(socket.SHUT_RD)
   client_socket.close()

   sys.exit(0)

except exception_handler, error:
   for msg in error.msgs:
      if (msg != ''):
         syslog.syslog(error.level, msg)
   sys.exit(1)
