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
from osutil import run_cmd


# Configuration exception
class ConfigError(Exception):
   def __init__(self, msg):
      self.msg = msg


def read_condor_config(subsys, attr_list):
   """ Uses condor_config_val to look up values in condor's configuration.
       First looks for subsys_param, then for the newer subsys.param.
       Returns map(param, value)"""
   config = {}
   if attr_list == []:
      (rcode, value, stderr) = run_cmd('condor_config_val', '%s' % (subsys))
      if rcode == 0:
         config[subsys.lower()] = value.strip()
      else:
         # Config value not found.  Raise an exception
         raise ConfigError('"%s" is not defined' % subsys)
   else:
      for attr in attr_list:
         (rcode, value, stderr) = run_cmd('condor_config_val', '%s_%s' % (subsys, attr))
         if rcode == 0:
            config[attr.lower()] = value.strip()
         else:
            # Try the newer <subsys>.param form
            (rcode, value, stderr) = run_cmd('condor_config_val', '%s.%s' % (subsys, attr))
            if rcode == 0:
               config[attr.lower()] = value.strip()
            else:
               # Config value not found.  Raise an exception
               raise ConfigError('"%s_%s" is not defined' % (subsys, attr))
   return config


def read_config_file(config_file, section):
   """Given configuration file and section names, returns a list of all value
     	 pairs in the config file as a dictionary"""
   parser = ConfigParser.ConfigParser()

   # Parse the config file
   if os.path.exists(config_file) == False:
      raise ConfigError('%s configuration file does not exist.' % config_file)
   else:
      try:
         parser.readfp(open(config_file))
         items = parser.items(section)
      except Exception, error:
         raise ConfigError('Problems reading %s.' % config_file, str(error))

      # Take the list of lists and convert into a dictionary
      dict = {}
      for list in items:
         dict[list[0]] = list[1].strip()
      return dict
