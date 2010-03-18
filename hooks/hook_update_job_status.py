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
import logging.handlers
import os
from condorutils.workfetch import *
from condorutils.socketutil import *
from condorutils.osutil import *
from condorutils.readconfig import *


def main(argv=None):
   if argv is None:
      argv = sys.argv

   size = {}
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
      size = read_condor_config('MAX_JOB_HOOKS', ['LOG'])
   except:
      size['log'] = 1000000

   base_logger = logging.getLogger(log_name)
   hndlr = logging.handlers.RotatingFileHandler(filename='%s.update' % config['log'],
                                                mode='a',
                                                maxBytes=int(size['log']),
                                                backupCount=1)
   hndlr.setLevel(logging.INFO)
   base_logger.setLevel(logging.INFO)
   fmtr = logging.Formatter('%(asctime)s %(levelname)s:%(message)s',
                            '%m/%d %H:%M:%S')
   hndlr.setFormatter(fmtr)
   base_logger.addHandler(hndlr)

   # Create a update_job_status message
   request = condor_wf()
   request.type = condor_wf_types.update_job_status

   # Store the ClassAd from STDIN in the data portion of the message
   request.data = ''
   for line in sys.stdin:
      request.data = request.data + str(line)

      # Send the message
   client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   try:
      client_socket.connect((config['ip'], int(config['port'])))
      client_socket.send(pickle.dumps(request, 2))
   except Exception, error:
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
