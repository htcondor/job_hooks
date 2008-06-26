#!/usr/bin/python
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

#   TEST INFORMATION:
#   This test will test that a job that depends on files external to the
#   execute node are transfered to the syste, and that the result files
#   are also transfered off the system.
#
#   When complete, there will be a test.zip and results.zip file in the
#   directory the test was run from.  The test.zip is the uncompressed
#   archive that is passed to the system as the data files, and the reults.zip
#   is the uncompressed archive that contains the results.  The archives
#   should be extracted to verify correct results.  The test relies on the
#   test_run.sh script being in the directory where the test is run.

import qpid
import time
import zipfile
import sys
import getopt
from qpid.util import connect
from qpid.datatypes import Message, RangedSet, uuid4
from qpid.connection import Connection
from qpid.queue import Empty
from caro.common import *

def dump_queue(queue_name, session):

   print 'Messages queue: ' + queue_name 

   # Create the local queue. Use the queue name as destination name
   dest = queue_name 
   queue = session.incoming(dest)

   # Subscribe the local queue to the queue on the server
   session.message_subscribe(queue=queue_name, destination=dest, accept_mode=session.accept_mode.explicit)
   session.message_flow(dest, session.credit_unit.message, 0xFFFFFFFF)
   session.message_flow(dest, session.credit_unit.byte, 0xFFFFFFFF)

   # Read responses as they come in and print to the screen.
   message = 0
   count = 0
   expected = 2
   to = 5

   while True:
      try:
         message = queue.get(timeout=to)
         content = message.body
         job_data = message.get('message_properties').application_headers
         count = count + 1
         print 'Headers:'
         for header in job_data.keys():
            print header + ': ' + job_data[header]
         print ''
         print 'Body: '
         print content
         print ''
         if content != None:
            file = open('results.zip', 'wb')
            file.write(content)
            file.close()
      except Empty:
         if count < expected:
            print 'Only received %d messages but expected %d.  TEST FAILED!' % (count, expected)
         else:
            print 'Received %d messages.  Check the results.zip for verification of test.' % count
         break
      except:
         print 'Unexpected exception!'
         break

      if message != 0:
        session.message_accept(RangedSet(message.id))

   return (0)

def main(argv=None):
   #----- Initialization ----------------------------
   if argv is None:
      argv = sys.argv

   #  Set parameters for login
   broker_info = read_config_file('Broker')

   replyTo = str(uuid4())
   pid = os.fork()
   if pid != 0:
      #  Create a client and log in to it.
      parent_socket = connect(str(broker_info['ip']), int(broker_info['port']))
      connection = Connection(sock=parent_socket)
      connection.start()

      session = connection.session(str(uuid4()))

      session.queue_declare(queue=broker_info['queue'], exclusive=False)
      session.exchange_bind(exchange=broker_info['exchange'], queue=broker_info['queue'], binding_key='grid')

      zip = zipfile.ZipFile('test.zip', 'w')
      zip.write('test_run.sh')
      zip.close()
      archived_file = open ('test.zip', 'rb')
      file_data = archived_file.read()
      archived_file.close()

      work_headers = {}
      work_headers['Cmd'] = '"test_run.sh"'
      work_headers['Iwd'] = '"."'
      work_headers['Owner'] = '"someone"'
      work_headers['result_files'] = '"output output2 output3"'
      message_props = session.message_properties(application_headers=work_headers)
      message_props.reply_to = session.reply_to(broker_info['exchange'], replyTo)
      message_props.message_id = str(uuid4())

      delivery_props = session.delivery_properties(routing_key='grid')
      delivery_props.ttl = 10000

      session.message_transfer(destination=broker_info['exchange'], message=Message(message_props, delivery_props, file_data))
      message_props.message_id = str(uuid4())
      os.waitpid(pid, 0)

      # Close the session before exiting so there are no open threads.
      session.close(timeout=10)
      connection.close()
   else:
      #  Create a client and log in to it.
      child_socket = connect(str(broker_info['ip']), int(broker_info['port']))
      child_connection = Connection(sock=child_socket)
      child_connection.start()
      child_session = child_connection.session(str(uuid4()))
      child_session.queue_declare(queue=replyTo, exclusive=True)
      child_session.exchange_bind(exchange=broker_info['exchange'], queue=replyTo, binding_key=replyTo)
      dump_queue(replyTo, child_session)
      child_session.close(timeout=10)
      child_connection.close()
   return(SUCCESS)

if __name__ == '__main__':
    sys.exit(main())