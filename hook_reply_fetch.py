#!/usr/bin/python

from amqp_common import *
import socket
import pickle
import sys
import os
import syslog

# Open a connection to the system logger
syslog.openlog (os.path.basename(sys.argv[0]))

try:
   try:
      config = read_config_file("AMQP_Module")
   except config_err, error:
      raise exception_handler(syslog.LOG_ERR, *(error.msg + ("Exiting.","")))

   # Create a reply_fetch notification
   request = condor_wf()
   reply_type = sys.argv[1]
   if reply_type == "accept":
      request.type = condor_wf_types.reply_claim_accept
   elif reply_type == "reject":
      request.type = condor_wf_types.reply_claim_reject

   # Store the ClassAd from STDIN in the data portion of the message
   request.data = ""
   for line in sys.stdin:
      request.data = request.data + str(line)

   # Send the message
   client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   client_socket.connect((config['ip'], int(config['port'])))
   client_socket.send(pickle.dumps(request, 2))
   client_socket.shutdown(socket.SHUT_RD)
   client_socket.close()

   sys.exit(0)

except exception_handler, error:
   for msg in error.msgs:
      if (msg != ''):
         syslog.syslog(error.level, msg)
   sys.exit(1)
