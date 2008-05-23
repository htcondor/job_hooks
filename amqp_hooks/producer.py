#!/usr/bin/python

import qpid
import base64
import time
import zipfile
from qpid.client import Client
from qpid.content import Content
from qpid.queue import Empty
from amqp_common import *

def dump_queue(client, queue_name, session):

   print "Messages queue: " + queue_name 

   # Create the local queue. Use the queue name as destination name

   dest = queue_name 
   queue = client.queue(dest)

   # Subscribe the local queue to the queue on the server

   session.message_subscribe(queue=queue_name, destination=dest, confirm_mode = 1)
   session.message_flow(dest, 0, 0xFFFFFFFF)
   session.message_flow(dest, 1, 0xFFFFFFFF)

   # Read responses as they come in and print to the screen.

   message = 0
   count = 0
   to = 20

   time.sleep(2)
   while True:
      try:
         message = queue.get(timeout=to)
         count = count + 1
#         content = message.content.body
         job_data = message.content['application_headers']
         print "Headers:"
         for header in job_data.keys():
            print header + ": " + job_data[header]
         print ""
#         print "Body: "
#         print content
#          file = open("results.zip", "wb")
#          file.write(content)
#          file.close()
      except Empty:
#         print "Received %s messages: %s" % (str(count), str(time.localtime()))
         print "Received %s messages: %s" % (str(count), str(time.time() - to))
#         print "No more messages!"
         break
      except:
         print "Unexpected exception!"
         break

      if message != 0:
        message.complete(cumulative=False)


   return (0)

#----- Initialization ----------------------------

#  Set parameters for login

host="127.0.0.1"
port=5672
amqp_spec="/usr/share/amqp/amqp.0-10-preview.xml"
user="guest"
password="guest"

#  Create a client and log in to it.

client = Client(host, port, qpid.spec.load(amqp_spec))
client.start({"LOGIN": user, "PASSWORD": password})

session = client.session()
session_info = session.session_open()
session_id = session_info.session_id

session.queue_declare(queue="grid", exclusive=False)
session.queue_bind(exchange="amq.direct", queue="grid", routing_key="grid")

replyTo = "ReplyTo:" + base64.urlsafe_b64encode(session_id)
#session.queue_declare(queue=replyTo, exclusive=True)
#session.queue_bind(exchange="amq.direct", queue=replyTo, routing_key=replyTo)

zip = zipfile.ZipFile("test.zip", "w")
zip.write("test_run.sh")
zip.close()
archived_file = open ("test.zip", "rb")
file_data = archived_file.read()
archived_file.close()

#work_request = Content(file_data, properties={"application_headers":{'Cmd': "", 'Arguments': "", 'Iwd' : "", 'Owner' : "", 'User' : ""}})
work_request = Content(file_data, properties={"application_headers":{}})
#work_request = Content('', properties={"application_headers":{'Cmd': "", 'Arguments': "", 'Iwd' : "", 'Owner' : "", 'User' : ""}})
work_request["message_id"] = base64.urlsafe_b64encode(session_id)
work_request["ttl"] = 10000
#work_request["application_headers"]["Cmd"] = "test_run.sh"
work_request["application_headers"]["Cmd"] = "\"/bin/true\""
#work_request["application_headers"]["Cmd"] = "/bin/sleep"
#work_request["application_headers"]["Arguments"] = "60"
work_request["application_headers"]["Iwd"] = "\"/tmp\""
work_request["application_headers"]["Owner"] = "\"bob\""
work_request["application_headers"]["User"] = "\"bob@redhat.com\""
#work_request["application_headers"]["result_files"] = "output output2 output3"
work_request["application_headers"]["Field1"] = "\"value\""
work_request["application_headers"]["Field2"] = "3.125345"
work_request["application_headers"]["Field3"] = "2"
work_request["routing_key"] = "grid"
work_request["reply_to"] = client.spec.struct("reply_to")
work_request["reply_to"]["exchange_name"] = "amq.direct"
work_request["reply_to"]["routing_key"] = replyTo
#session.message_transfer(destination="amq.direct", content=work_request)
#work_request["message_id"] = ""
#session.message_transfer(destination="amq.direct", content=work_request)

pid = os.fork()
if pid != 0:
   count = 0
   time.sleep(2)
#   print "Started sending messages: " + str(time.localtime())
   print "Started sending messages: " + str(time.time())
   for num in range(0,1):
      session.message_transfer(destination="amq.direct", content=work_request)
      work_request["message_id"] = base64.urlsafe_b64encode("154582592462058724" + str(num))
      count = num
#   print "Finished sending %s messages: %s" % (str(count + 1), str(time.localtime()))
   print "Finished sending %s messages: %s" % (str(count + 1), str(time.time()))
   os.waitpid(pid, 0)
else:
   child_client = Client(host, port, qpid.spec.load(amqp_spec))
   child_client.start({"LOGIN": user, "PASSWORD": password})
   child_session = child_client.session()
   child_session_info = child_session.session_open()
   child_session.queue_declare(queue=replyTo, exclusive=True)
   child_session.queue_bind(exchange="amq.direct", queue=replyTo, routing_key=replyTo)
   replyTo = "ReplyTo:" + base64.urlsafe_b64encode(session_id)
   dump_queue(child_client, replyTo, child_session)
   child_session.session_close()

# Close the session before exiting so there are no open threads.

session.session_close()
