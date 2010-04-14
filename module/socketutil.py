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


# SocketError exception
class SocketError(Exception):
   def __init__(self, msg):
      self.msg = msg


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
      try:
         close_socket(sock)
      except:
         pass
      if error != None:
         raise SocketError('socket error %d: %s' % (error[0], error[1]))
   sock.settimeout(old_timeout)
   return msg


def close_socket(connection):
   """Performs a shutdown and a close on the socket.  Any errors
      are logged to the system logging service.  Raises a SocketError
      if any errors are encountered"""
   try:
      try:
         # python 2.3 doesn't have SHUT_WR defined, so use it's value (1)
         connection.shutdown(1)
      except Exception, error:
         if error != None:
            raise SocketError('socket error %d: %s' % (error[0], error[1]))
      try:
         data = connection.recv(4096)
         while len(data) != 0:
            data = connection.recv(4096)
      except:
         pass
   finally:
      connection.close()
      connection = None
