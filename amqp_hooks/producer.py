#!/usr/bin/python

import qpid
import base64
import time
import zipfile
from qpid.util import connect
from qpid.datatypes import Message, RangedSet, uuid4
from qpid.connection import Connection
#from qpid.client import Client
#from qpid.content import Content
from qpid.queue import Empty
from amqp_common import *

def dump_queue(queue_name, session):

   print "Messages queue: " + queue_name 

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
   to = 20

   while True:
      try:
         message = queue.get(timeout=to)
         count = count + 1
         if count == 1:
            print "Received first reponse: %s " % str(time.time())
#         content = message.body
#         job_data = message.get('message_properties').application_headers
#         print "Headers:"
#         for header in job_data.keys():
#            print header + ": " + job_data[header]
#         print ""
#         print "Body: "
#         print content
#         if content != None:
#            file = open("results.zip", "wb")
#            file.write(content)
#            file.close()
      except Empty:
         print "Received %s messages: %s" % (str(count), str(time.time() - to))
         break
      except:
         print "Unexpected exception!"
         break

      if message != 0:
        session.message_accept(RangedSet(message.id))

   return (0)

#----- Initialization ----------------------------

#  Set parameters for login
host="127.0.0.1"
port=5672

replyTo = "reply_to: work_reply_queue"
pid = os.fork()
if pid != 0:
   #  Create a client and log in to it.
   parent_socket = connect(host, port)
   connection = Connection(sock=parent_socket)
   connection.start()

   session = connection.session(str(uuid4()))

   session.queue_declare(queue="grid", exclusive=False)
   session.exchange_bind(exchange="amq.direct", queue="grid", binding_key="grid")

   zip = zipfile.ZipFile("test.zip", "w")
   zip.write("test_run.sh")
   zip.close()
   archived_file = open ("test.zip", "rb")
   file_data = archived_file.read()
   archived_file.close()

   file_data = ""
   work_headers = {}
#   work_headers["Cmd"] = "\"test_run.sh\""
   work_headers["Cmd"] = "\"/bin/true\""
#   work_headers["Cmd"] = "\"/bin/sleep\""
#   work_headers["Arguments"] = "60"
#   work_headers["Iwd"] = "\"/tmp\""
   work_headers["Iwd"] = "\".\""
   work_headers["Owner"] = "\"bob\""
   work_headers["User"] = "\"bob@redhat.com\""
#   work_headers["result_files"] = "\"output output2 output3\""
   work_headers["Field1"] = "\"value\""
   work_headers["Field2"] = "3.125345"
   work_headers["Field3"] = "2"
   message_props = session.message_properties(application_headers=work_headers)
   message_props.reply_to = session.reply_to("amq.direct", replyTo)
   message_props.message_id = str(uuid4())

   delivery_props = session.delivery_properties(routing_key="grid")
   delivery_props.ttl = 10000

   count = 0
   time.sleep(2)
   ids = {}
   print "Started sending messages: " + str(time.time())
   for num in range(0,1000):
      session.message_transfer(destination="amq.direct", message=Message(message_props, delivery_props, file_data))
      message_props.message_id = str(uuid4())
      count = num
   print "Finished sending %s messages: %s" % (str(count + 1), str(time.time()))
   os.waitpid(pid, 0)

   # Close the session before exiting so there are no open threads.
   session.close(timeout=10)
else:
   #  Create a client and log in to it.
   child_socket = connect(host, port)
   child_connection = Connection(sock=child_socket)
   child_connection.start()
   child_session = child_connection.session(str(uuid4()))
   child_session.queue_declare(queue=replyTo, exclusive=True)
   child_session.exchange_bind(exchange="amq.direct", queue=replyTo, binding_key=replyTo)
   dump_queue(replyTo, child_session)
   child_session.close(timeout=10)

