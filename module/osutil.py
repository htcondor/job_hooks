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
   elif os.name == 'nt' or os.name == 'ce':
      env = copy.deepcopy(os.environ)
      for param in environ.keys():
         env[param] = environ[param]
   else:
      env = copy.deepcopy(environ)
   if os.name != 'nt' and os.name != 'ce':
      env['PATH'] = '/bin:/usr/bin:/usr/local/bin:/sbin:/usr/sbin:/usr/local/sbin:%s' % os.environ['PATH']
   else:
      # Use the OS defined path
      env['PATH'] = os.environ['PATH']
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
      try:
         if os.name == 'nt' or os.name == 'ce':
            cmd_list = _cmdline2list(cmd)
         else:
            cmd_list = shlex.split(cmd)
         obj = Popen(cmd_list, stdout=PIPE, stderr=PIPE, env=env)
         (std_out, std_err) = obj.communicate()
         retcode = obj.returncode
      except:
         return (-1, None, None)
   else:
      if environ != {}:
         old_env = copy.deepcopy(os.environ)
         try:
            for var in env.keys():
               os.environ[var] = env[var]
         except:
            return (-1, None, None)

      try:
         obj = Popen3(cmd, True)
      except:
         return (-1, None, None)

      try:
         std_out = ''
         for line in obj.fromchild:
            std_out = std_out + line
         obj.fromchild.close()
      except:
         pass
      try:
         obj.tochild.close()
      except:
         pass
      try:
         std_err = ''
         for line in obj.childerr:
            std_err = std_err + line
         obj.childerr.close()
      except:
         pass

      retcode = obj.wait()
      if environ != {}:
         for var in env.keys():
            del os.environ[var]
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
      perms = info.external_attr >> 16L
      if perms > 0:
         os.chmod(name, perms)
      os.utime(name, (file_time, file_time))


def tarball_extract(filename):
   """Extracts the tarball (.tar.gz) given"""
   tarball = tarfile.open(filename, 'r:gz')
   for file in tarball.getnames():
      tarball.extract(file)
   tarball.close()


# This method comes from the jython code base.
def _cmdline2list(cmdline):
   """Build an argv list from a Microsoft shell style cmdline str
      following the MS C runtime rules."""

   whitespace = ' \t'
   # count of preceding '\'
   bs_count = 0
   in_quotes = False
   arg = []
   argv = []

   for ch in cmdline:
      if ch in whitespace and not in_quotes:
         if arg:
            # finalize arg and reset
            argv.append(''.join(arg))
            arg = []
         bs_count = 0
      elif ch == '\\':
         arg.append(ch)
         bs_count += 1
      elif ch == '"':
         if not bs_count % 2:
            # Even number of '\' followed by a '"'. Place one
            # '\' for every pair and treat '"' as a delimiter
            if bs_count:
               del arg[-(bs_count / 2):]
            in_quotes = not in_quotes
         else:
            # Odd number of '\' followed by a '"'. Place one '\'
            # for every pair and treat '"' as an escape sequence
            # by the remaining '\'
            del arg[-(bs_count / 2 + 1):]
            arg.append(ch)
         bs_count = 0
      else:
         # regular char
         arg.append(ch)
         bs_count = 0

   # A single trailing '"' delimiter yields an empty arg
   if arg or in_quotes:
      argv.append(''.join(arg))

   return argv
