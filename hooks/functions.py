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
import re
import tarfile
import zipfile
import time
try:
   from subprocess import *
   use_popen2 = False
except:
   from popen2 import *
   use_popen2 = True
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
           self.__type__ = thetype

    def get_type(self):
        return self.__type__

    type = property(get_type, set_type)

    def set_data(self, string):
           self.__data__ = string

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
   def __init__(self, msg):
      self.msg = msg

def run_cmd(cmd, args):
   """Runs the command specified in 'cmd' with the given 'args' using
      either the subprocess module or the open2 module, depending on which
      is supported.  The subprocess module is favored.  Returns
      (return_code, stdout, stderr)"""
   retcode = -1
   std_out = ''
   std_err = ''
   if use_popen2 == False:
      obj = Popen([cmd, args], stdout=PIPE, stderr=PIPE)
      (std_out, std_err) = obj.communicate()
      retcode = obj.returncode
   else:
      obj = Popen3('%s %s' % (cmd, args), True)
      retcode = obj.wait()
      try:
         std_out = obj.fromchild.readlines()[0]
         obj.fromchild.close()
      except:
         pass
      try:
         obj.tochild.close()
      except:
         pass
      try:
         std_err = obj.childerr.readlines()[0]
         obj.childerr.close()
      except:
         pass
   return ([retcode, std_out, std_err])
       
def read_condor_config(subsys, attr_list):
   """ Uses condor_config_val to look up values in condor's configuration.
       First looks for subsys_param, then for the newer subsys.param.
       Returns map(param, value)"""
   config = {}
   for attr in attr_list:
      (rcode, value, sterr) = run_cmd('condor_config_val', '%s_%s' % (subsys, attr))
      if rcode == 0:
         config[attr.lower()] = value.rstrip().lstrip()
      else:
         # Try the newer <subsys>.param form
         (rcode, value, sterr) = run_cmd('condor_config_val', '%s.%s' % (subsys, attr))
         if rcode == 0:
            config[attr.lower()] = value.rstrip().lstrip()
         else:
            # Config value not found.  Raise an exception
            raise config_err('"%s_%s" is not defined' % (subsys, attr))
   return config

def read_config_file(config_file, section):
   """Given configuration file and section names, returns a list of all value
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
         dict[list[0]] = list[1].rstrip().lstrip()
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
      if error != None:
         raise general_exception(syslog.LOG_ERR, 'socket error %d: %s' % (error[0], error[1]))
   sock.settimeout(old_timeout)
   return msg

def close_socket(connection):
   """Performs a shutdown and a close on the socket.  Any errors
      are logged to the system logging service.  Raises a general_exception
      if any errors are encountered"""
   try:
      try:
         # python 2.3 doesn't have SHUT_WR defined, so use it's value (1)
         connection.shutdown(1)
      except Exception, error:
         if error != None:
            raise general_exception(syslog.LOG_ERR, 'socket error %d: %s' % (error[0], error[1]))
      try:
         data = connection.recv(4096)
         while len(data) != 0:
            data = connection.recv(4096)
      except:
         pass
   finally:
      connection.close()
      connection = None

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

def grep(pattern, data):
   """Returns the first instance found of pattern in data.  If pattern
      doesn't exist in data, None is returned.  If data contains groups,
      returns the matching subgroups instead"""
   for line in data.split('\n'):
      match = re.match(pattern, line)
      if match != None:
         break
   if match != None and match.groups() != None:
      found = match.groups()
   else:
      found = match
   return(found)

def zip_extract(filename):
   """Unzips the contents of the filename given, preserving permissions and
      ownership"""
   zip = zipfile.ZipFile(filename, 'r')
   contents = zip.namelist()

   # Loop through the archive names and extract the contents
   # Make sure to create higher level directories before creating a lower
   # level file or directory (if applicable)
   contents.sort()
   for item in contents:
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
   for name in contents:
      info = zip.getinfo(name)
      file_time = time.mktime(info.date_time + (0, 0, -1))
      os.chmod(name, info.external_attr >> 16L)
      os.utime(name, (file_time, file_time))

def tarball_extract(filename):
   """Extracts the tarball (.tar.gz) given"""
   tarball = tarfile.open(filename, 'r:gz')
   for file in tarball.getnames():
      tarball.extract(file)
   tarball.close()
