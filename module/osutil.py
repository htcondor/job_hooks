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
import re
import tarfile
import zipfile
import time
import os
import shlex
import copy
from cStringIO import StringIO
try:
   from subprocess import *
   use_popen2 = False
except:
   from popen2 import *
   use_popen2 = True


def run_cmd(cmd, environ={}, inter=False):
   """Runs the command specified in 'cmd' with the given 'args' using
      either the subprocess module or the open2 module, depending on which
      is supported.  The subprocess module is favored.  Returns
      (return_code, stdout, stderr)"""
   retcode = -1
   std_out = None
   std_err = None
   if environ == {}:
      env = copy.deepcopy(os.environ)
   else:
      env = copy.deepcopy(environ)
   env['PATH'] = '/usr/local/bin:/bin:/usr/bin:/usr/local/sbin:/usr/sbin:/sbin'
   if inter == True:
      pid = os.fork()
      if pid == 0:
         cmd_list = shlex.split(cmd)
         os.execvpe(cmd_list[0], cmd_list, env)
      else:
         retcode = os.waitpid(pid, 0)[0]
         std_out = None
         std_err = None
   elif use_popen2 == False:
      cmd_list = shlex.split(cmd)
      obj = Popen(cmd_list, stdout=PIPE, stderr=PIPE, env=env)
      (std_out, std_err) = obj.communicate()
      retcode = obj.returncode
   else:
      if environ != {}:
         old_env = copy.deepcopy(os.environ)
         try:
            for var in env.keys():
               os.environ[var] = env[var]
         except:
            return ([-1, None, None])

      obj = Popen3(cmd, True)
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

      if environ != {}:
         os.environ = copy.deepcopy(old_env)
   return (retcode, std_out, std_err)


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
