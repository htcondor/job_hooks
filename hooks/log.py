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
import logging
import logging.handlers
import sys

def create_file_logger(name, file, level, mode='a', size=1000000, bcknum=1):
   logger = logging.getLogger(name)
   hndlr = logging.handlers.RotatingFileHandler(filename=file,
                                                mode=mode,
                                                maxBytes=int(size),
                                                backupCount=bcknum)
   hndlr.setLevel(level)
   logger.setLevel(level)
   fmtr = logging.Formatter('%(asctime)s %(levelname)s: %(message)s',
                            '%m/%d %H:%M:%S')
   hndlr.setFormatter(fmtr)
   logger.addHandler(hndlr)
   return(logger)


def add_debug_console(logger):
   hndlr = logging.StreamHandler(sys.stderr)
   hndlr.setLevel(logging.DEBUG)
   fmtr = logging.Formatter('%(asctime)s %(levelname)s: %(message)s',
                            '%m/%d %H:%M:%S')
   hndlr.setFormatter(fmtr)
   logger.addHandler(hndlr)


def log(level, logger_name, *msgs):
   """Logs messages in the passed msgs to the logger with the provided
      logger_name."""
   logger = logging.getLogger(logger_name)
   for msg in msgs:
      if (msg != ''):
         logger.log(level, msg)
