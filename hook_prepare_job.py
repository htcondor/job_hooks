#!/usr/bin/python

import socket
import pickle
import sys
import time
import os
import zipfile
import syslog
from cStringIO import StringIO
from amqp_common import *

def zip_extract(filename):
   zip = zipfile.ZipFile(filename, "r")
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

         file = open(item, 'wb')
         file_str = StringIO(zip.read(item))
         buffer_length = 2 ** 20
         data = file_str.read(buffer_length)
         while data:
            file.write(data)
            data = file_str.read(buffer_length)
         file.flush()
         file.close()

   # Set the perserved permissions and timestamp for the extracted
   # files/directories
   for name in sorted(contents):
      info = zip.getinfo(name)
      file_time = time.mktime(info.date_time + (0, 0, -1))
      os.chmod(name, info.external_attr >> 16L)
      os.utime(name, (file_time, file_time))

# Open a connection to the system logger
syslog.openlog (os.path.basename(sys.argv[0]))

try:
   try:
      config = read_config_file("AMQP_Module")
   except config_err, error:
      raise exception_handler(syslog.LOG_ERR, *(error.msg + ("Exiting.","")))

   # Create a prepare_job notification
   request = condor_wf()
   request.type = condor_wf_types.prepare_job

   # Store the ClassAd from STDIN in the data portion of the message
   cwd = os.getcwd()
   request.data = ""
   for line in sys.stdin:
      request.data = request.data + str(line)
   request.data = request.data + "OriginatingCWD = \"" + cwd + "\"\n"

   # Send the message
   client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   client_socket.connect ((config['ip'], int(config['port'])))
   client_socket.send (pickle.dumps(request, 2))

   # Receive the reply from the prepare_job notification 
   reply = socket_read_all(client_socket)
   client_socket.shutdown(socket.SHUT_RD)
   client_socket.close()
   decoded = pickle.loads(reply)
   filename = decoded.data

   # Extract the archive if it exists
   if filename != '':
      # Determine the type of archive and then extract it
      zip_extract(filename)

   sys.exit(0)

except exception_handler, error:
   for msg in error.msgs:
      if (msg != ''):
         syslog.syslog(error.level, msg)
   sys.exit(1)
