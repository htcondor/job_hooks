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
import time
import os
import zipfile
import syslog
from caro.common import *

def zip_extract(filename):
   zip = zipfile.ZipFile(filename, 'r')
   contents = zip.namelist()

   # Loop through the archive names and extract the contents
   # Make sure to create higher level directories before creating a lower
   # level file or directory (if applicable)
   for item in sorted(contents):
      if item.endswith('/'):
         # This item is all directories, so recursively create them if
         # they don't already exist
         if not os.path.exists(item):
            os.makedirs(item)
      else:
         # This is a directory + file or a file by itself, so create the
         # directory hierarchy first (if applicable) then extract the file.
         dirs = item.split('/')
         dir_structure = ''
         for count in range(0,len(dirs)-1):
            full_path = os.path.join(dir_structure, dirs[count])
            if dirs[count] != '' and not os.path.exists(full_path):
               os.mkdir(full_path)
            dir_structure = full_path

         write_file(item, zip.read(item))

   # Set the perserved permissions and timestamp for the extracted
   # files/directories
   for name in sorted(contents):
      info = zip.getinfo(name)
      file_time = time.mktime(info.date_time + (0, 0, -1))
      os.chmod(name, info.external_attr >> 16L)
      os.utime(name, (file_time, file_time))

def main(argv=None):
   if argv is None:
      argv = sys.argv

   # Open a connection to the system logger
   syslog.openlog(os.path.basename(argv[0]))

   try:
      try:
         config = read_config_file('AMQP_Module')
      except config_err, error:
         raise general_exception(syslog.LOG_ERR, *(error.msg + ('Exiting.','')))

      # Create a prepare_job notification
      request = condor_wf()
      request.type = condor_wf_types.prepare_job

      # Store the ClassAd from STDIN in the data portion of the message
      cwd = os.getcwd()
      request.data = ''
      for line in sys.stdin:
         request.data = request.data + str(line)
      request.data = request.data + 'OriginatingCWD = "' + cwd + '"\n'

      # Send the message
      client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      try:
         client_socket.connect((config['ip'], int(config['port'])))
         client_socket.send (pickle.dumps(request, 2))
      except Exception, error:
         close_socket(client_socket)
         raise general_exception(syslog.LOG_ERR, 'socket error %d: %s' % (error[0], error[1]))

      # Receive the reply from the prepare_job notification 
      reply = socket_read_all(client_socket)
      close_socket(client_socket)
      decoded = pickle.loads(reply)
      filename = decoded.data

      # Extract the archive if it exists
      if filename != '':
         # Determine the type of archive and then extract it
         zip_extract(filename)

      return(SUCCESS)

   except general_exception, error:
      log_messages(error)
      return(FAILURE)

if __name__ == '__main__':
    sys.exit(main())
