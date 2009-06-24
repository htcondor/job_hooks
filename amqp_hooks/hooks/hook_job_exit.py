#!/usr/bin/python
#   Copyright 2008 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import socket
import pickle
import sys
import syslog
import os
from jobhooks.functions import *

def main(argv=None):
   if argv is None:
      argv = sys.argv

   # Open a connection to the system logger
   syslog.openlog(os.path.basename(argv[0]))

   try:
      try:
         config = read_config_file('/etc/condor/job-hooks.conf', 'Hooks')
      except config_err, error:
         raise general_exception(syslog.LOG_ERR, *(error.msg + ('Exiting.','')))

      # Create an exit message
      msg = condor_wf()
      exit_status = sys.argv[1]
      if exit_status == 'exit':
         msg.type = condor_wf_types.exit_exit
      elif exit_status == 'remove':
         msg.type = condor_wf_types.exit_remove
      elif exit_status == 'hold':
         msg.type = condor_wf_types.exit_hold
      elif exit_status == 'evict':
         msg.type = condor_wf_types.exit_evict
      else:
         raise general_exception(syslog.LOG_ERR, 'Unknown exit status received: %s' % exit_status)

      # Store the ClassAd from STDIN in the data portion of the message
      cwd = os.getcwd()
      msg.data = ''
      for line in sys.stdin:
         msg.data = msg.data + str(line)
      msg.data = msg.data + 'OriginatingCWD = "' + cwd + '"\n'

      # Send the message
      client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      try:
         client_socket.connect((config['ip'], int(config['port'])))
         client_socket.send(pickle.dumps(msg, 2))
      except Exception, error:
         close_socket(client_socket)
         raise general_exception(syslog.LOG_ERR, 'socket error %d: %s' % (error[0], error[1]))

      # Get acknowledgement that the exit work has completed
      try:
         reply = socket_read_all(client_socket)
      except:
         close_socket(client_socket)
         raise general_exception(syslog.LOG_ERR, 'socket error %d: %s' % (error[0], error[1]))
      close_socket(client_socket)

      return(SUCCESS)

   except general_exception, error:
      log_messages(error)
      return(FAILURE)

if __name__ == '__main__':
    sys.exit(main())
