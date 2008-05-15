import ConfigParser
import os
import socket

class wf_type:
   def __init__(self,list=[]):
      count = 0
      for item in list.split():
         vars(self)[item] = count
         count = count + 1

   def __setattr__(self, name, value):
      raise ValueError("Modifying values is not allowed")

   def __delattr__(self, name):
      raise ValueError("Deleting entries is not allowed")

condor_wf_types = wf_type("get_work prepare_job reply_claim_accept reply_claim_reject update_job_status exit_exit exit_remove exit_hold exit_evict")

class condor_wf(object):
    def set_type(self, thetype):
        self.__type__ = int(thetype)

    def get_type(self):
        return self.__type__

    type = property(get_type, set_type)

    def set_msg_num(self, number):
        self.__msg_num__ = int(number)

    def get_msg_num(self):
        return self.__msg_num__

    msg_num = property(get_msg_num, set_msg_num)

    def set_data(self, string):
        self.__data__ = str(string)

    def get_data(self):
        return self.__data__

    data = property(get_data, set_data)

class exception_handler(Exception):
   def __init__(self, level, *msgs):
      self.level = level
      self.msgs = msgs

class config_err(Exception):
   def __init__(self, *str):
      print str
      self.msg = str

def read_config_file(section):
   """Given a section name, returns a list of all value pairs in the
      config file as a dictionary"""
   config_file = "/etc/opt/grid/grid_amqp.conf"
   parser = ConfigParser.ConfigParser()

   # Parse the config file
   if os.path.exists(config_file) == False:
      raise config_err("%s configuration file doesn't exist." % config_file)
   else:
      try:
         parser.readfp(open(config_file))
         items = parser.items(section)
      except Exception, error:
         raise config_err("Problems reading %s." % config_file, str(error))

      # Take the list of lists and convert into a dictionary
      dict = {}
      for list in items:
         dict[list[0]] = list[1]
      return dict

def socket_read_all(sock):
   """Read all waiting to be read on the given socket.  The first attempt to
      read will be a blocking call, and all subsequent reads will be
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
   sock.settimeout(old_timeout)
   return msg
