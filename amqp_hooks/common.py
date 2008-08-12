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

import ConfigParser
import os
import socket
import syslog
from cStringIO import StringIO

SUCCESS = 0
FAILURE = 1

# Generic enumerated type
class wf_type:
   def __init__(self,list=[]):
      count = 0
      for item in list.split():
         vars(self)[item] = count
         count = count + 1

   def __setattr__(self, name, value):
      raise ValueError('Modifying values is not allowed')

   def __delattr__(self, name):
      raise ValueError('Deleting entries is not allowed')

# The type of requests from condor to act upon
condor_wf_types = wf_type('get_work prepare_job reply_claim_accept reply_claim_reject update_job_status exit_exit exit_remove exit_hold exit_evict')

# The information about the job
class condor_wf(object):
    def set_type(self, thetype):
        self.__type__ = int(thetype)

    def get_type(self):
        return self.__type__

    type = property(get_type, set_type)

    def set_data(self, string):
        self.__data__ = str(string)

    def get_data(self):
        return self.__data__

    data = property(get_data, set_data)

# General failure exception
class general_exception(Exception):
   def __init__(self, level, *msgs):
      self.level = level
      self.msgs = msgs

# Configuration exception
class config_err(Exception):
   def __init__(self, *str):
      print str
      self.msg = str

def read_config_file(config_file, section):
   """Given config file and section names, returns a list of all value
      pairs in the config file as a dictionary"""
   parser = ConfigParser.ConfigParser()

   # Parse the config file
   if os.path.exists(config_file) == False:
      raise config_err('%s configuration file does not exist.' % config_file)
   else:
      try:
         parser.readfp(open(config_file))
         items = parser.items(section)
      except Exception, error:
         raise config_err('Problems reading %s.' % config_file, str(error))

      # Take the list of lists and convert into a dictionary
      dict = {}
      for list in items:
         dict[list[0]] = list[1]
      return dict

def socket_read_all(sock):
   """Read all data waiting to be read on the given socket.  The first attempt
      to read will be a blocking call, and all subsequent reads will be
      non-blocking."""
   msg = ''
   old_timeout = sock.gettimeout()
   data = sock.recv(1024)
   sock.settimeout(0.1)
   try:
      while len(data) != 0:
         msg += data
         data = sock.recv(1024)
   except socket.timeout, timeout:
      pass
   except Exception, error:
      close_socket(sock)
      raise general_exception(syslog.LOG_ERR, 'socket error %d: %s' % (error[0], error[1]))
   sock.settimeout(old_timeout)
   return msg

def close_socket(connection):
   """Performs a shutdown and a close on the socket.  Any errors
      are logged to the system logging service.  Raises a general_exception
      if any errors are encountered"""
   try:
      try:
         connection.shutdown(socket.SHUT_RDWR)
      except Exception, error:
         raise general_exception(syslog.LOG_ERR, 'socket error %d: %s' % (error[0], error[1]))
   finally:
      connection.close()

def log_messages(exception):
   """Logs messages in the passed general_exception exception to the
      system logger"""
   for msg in exception.msgs:
      if (msg != ''):
         syslog.syslog(exception.level, msg)

def write_file(filename, data):
   """Writes the given data into the given filename in pieces to account for
      large files"""
   file_ptr = open(filename, 'wb')
   file_str = StringIO(data)
   buffer_length = 2 ** 20
   contents = file_str.read(buffer_length)
   while contents:
      file_ptr.write(contents)
      contents = file_str.read(buffer_length)
   file_ptr.flush()
   file_ptr.close()

