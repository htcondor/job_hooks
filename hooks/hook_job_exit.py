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
import logging
import os
from condorutils import SUCCESS, FAILURE
from condorutils.workfetch import *
from condorutils.socketutil import *
from condorutils.osutil import *
from condorutils.readconfig import *
from condorutils.log import *


def main(argv=None):
   if argv is None:
      argv = sys.argv

   log_name = os.path.basename(argv[0])

   try:
      config = read_condor_config('JOB_HOOKS', ['IP', 'PORT', 'LOG'])
   except ConfigError, error:
      try:
         print >> sys.stderr, 'Warning: %s' % error.msg
         print >> sys.stderr, 'Attemping to read config from "/etc/condor/job-hooks.conf"'
         config = read_config_file('/etc/condor/job-hooks.conf', 'Hooks')
      except ConfigError, error:
         print >> sys.stderr, 'Error: %s. Exiting' % error.msg
         return(FAILURE)
   try:
      size = int(read_condor_config('MAX_JOB_HOOKS', ['LOG'])['log'])
   except:
      size = 1000000

   base_logger = create_file_logger(log_name, '%s.exit' % config['log'], logging.INFO, size=size)

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
      log_messages(logging.ERROR, log_name, 'Unknown exit status received: %s' % exit_status)
      return(FAILURE)

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
      try:
         close_socket(client_socket)
      except:
         pass
      log_messages(logging.ERROR, log_name, 'socket error %d: %s' % (error[0], error[1]))
      return(FAILURE)

   # Get acknowledgement that the exit work has completed
   try:
      reply = socket_read_all(client_socket)
   except:
      try:
         close_socket(client_socket)
      except:
         pass
      log_messages(logging.ERROR, log_name, 'socket error %d: %s' % (error[0], error[1]))
      return(FAILURE)

   try:
      close_socket(client_socket)
   except SocketError, error:
      log_messages(logging.WARNING, log_name, error.msg)

   return(SUCCESS)

if __name__ == '__main__':
    sys.exit(main())
