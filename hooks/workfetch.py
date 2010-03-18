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
