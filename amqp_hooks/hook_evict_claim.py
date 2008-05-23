#!/usr/bin/python

import socket
import pickle
import sys
import os
import syslog
from amqp_common import *

# Open a connection to the system logger
syslog.openlog (os.path.basename(sys.argv[0]))

try:
   try:
      config = read_config_file("AMQP_Module")
   except config_err, error:
      raise exception_handler(syslog.LOG_ERR, *(error.msg + ("Exiting.","")))

   # Create an evict claim
   request = condor_wf()
   request.type = condor_wf_types.evict_claim

   # Store the ClassAd from STDIN in the data portion of the message
   request.data = ""
   for line in sys.stdin:
      request.data = request.data + str(line)

   # Send the message
   client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   client_socket.connect ((config['ip'], int(config['port'])))
   client_socket.send (pickle.dumps(request, 2))
   client_socket.shutdown(socket.SHUT_RD)
   client_socket.close()

   sys.exit(0)

except exception_handler, error:
   for msg in error.msgs:
      if (msg != ''):
         syslog.syslog(error.level, msg)
   sys.exit(1)
