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

   # Create a get_work request
   request = condor_wf()
   request.type = condor_wf_types.get_work

   # Store the ClassAd from STDIN in the data portion of the message
   request.data = ''
   for line in sys.stdin:
      request.data = request.data + str(line)

   # Send the request
   client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   client_socket.connect((config['ip'], int(config['port'])))
   client_socket.send(pickle.dumps(request, 2))

   # Get receive the work information and print to stdout
   reply = socket_read_all(client_socket)
   client_socket.shutdown(socket.SHUT_RD)
   client_socket.close()
   decoded = pickle.loads(reply)
   if decoded.data != '':
      print decoded.data

   sys.exit(0)

except exception_handler, error:
   for msg in error.msgs:
      if (msg != ''):
         syslog.syslog(error.level, msg)
   sys.exit(1)
