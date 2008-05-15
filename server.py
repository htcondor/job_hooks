#!/usr/bin/python

import socket
import pickle
import sys
import os
import time
import qpid
import ConfigParser
import syslog
import re
import threading
import signal
import zipfile
import copy
from amqp_common import *
from qpid.client import Client
from qpid.content import Content
from qpid.queue import Empty

#class exception_handler(Exception):
#   def __init__(self, level, *msgs):
#      self.level = level
#      self.msgs = msgs

class exit_signal(Exception):
   def __init__(self, str):
      self.msg = str

class threadsafe_dict(object):
   def __init__(self):
      """Creates the default dictionary and sets up the lock"""
      self.__access_lock__ = threading.Lock()
      self.__list__ = {}

   def __lock__(self):
      """Acquires the lock"""
      self.__access_lock__.acquire(True)

   def __unlock__(self):
      """Releases the lock"""
      self.__access_lock__.release()

   def add(self, key, value):
      """Adds an entry to the dictionary.  Raises an exception if the key
         already exists in the dictionary"""
      if self.find(key) == False:
         self.__lock__()
         self.__list__.update({key:value})
         self.__unlock__()
      else:
         raise exception_handler(syslog.LOG_WARNING, "Key %s already exists." % key)

   def remove(self, key):
      """Removes an entry from the dictionary"""
      if self.find(key) == True:
         self.__lock__()
         value = self.__list__[key]
         del self.__list__[key]
         self.__unlock__()
         return value
      else:
         return Empty

   def get(self, key):
      """Returns the value associated with the provided key"""
      if self.find(key) == True:
         self.__lock__()
         value = self.__list__[key]
         self.__unlock__()
         return value
      else:
         return Empty

   def find(self, key):
      """Returns true if the desired key exists in the dictionary,
         false otherwise"""
      self.__lock__()
      value = self.__list__.has_key(key)
      self.__unlock__()
      return value

class threadsafe_list(object):
   def __init__(self):
      """Creates the default list and sets up the lock"""
      self.__access_lock__ = threading.Lock()
      self.__list__ = []

   def __lock__(self):
      """Acquires the lock"""
      self.__access_lock__.acquire(True)

   def __unlock__(self):
      """Releases the lock"""
      self.__access_lock__.release()

   def add(self, value):
      """Adds an entry to the list.  Raises an exception if the value
         already exists in the list"""
      if self.exists(value) == False:
         self.__lock__()
         self.__list__.append(value)
         self.__unlock__()
      else:
         raise exception_handler(syslog.LOG_WARNING, "Value %s already exists in the list." % value)

   def remove(self, value):
      """Removes an entry from the list.  Returns Empty if the entry
         doesn't exist in the list"""
      pos = int(self.__find__(value))
      if pos >= 0:
         self.__lock__()
         removed = self.__list__[pos]
         del self.__list__[pos]
         self.__unlock__()
         return removed
      else:
         return Empty

   def __find__(self, entry):
      """Returns the postition of the desired entry in the list.
         If the entry doesn't exist in the list, -1 is returned"""
      value = -1
      self.__lock__()
      for pos in range(0,len(self.__list__)):
         if entry == self.__list__[pos]:
            value = pos
            break
      self.__unlock__()
      return value

   def exists(self,entry):
      """Returns True is the entry is found in the list, otherwise False"""
      self.__lock__()
      value = entry in self.__list__
      self.__unlock__()
      return value

class global_data(object):
   def __init__(self):
      self.known_slots = threadsafe_list()
      self.AMQP_messages = threadsafe_dict()

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
   return found

def parse_data_into_AMQP_msg(data):
   """Takes the data and parses it into the headers specified in an AMQP
      message.  extra_args is excluded from this, as that is a more complicated
      field"""
   msg = Content(properties={'application_headers':{}})
   for line in data.split('\n'):
      found = grep('^(.+)\s*=\s*(.*)$', line)
      if found != None:
         msg['application_headers'][found[0]] = found[1]
   return msg

def send_AMQP_response(connection, orig_req, send_msg):
   """Sends send_msg to the reply_to queue in orig_req using the broker
      connection 'connection'"""
   send_msg["routing_key"] = orig_req.content["reply_to"]["routing_key"]
   connection.message_transfer(destination=orig_req.content["reply_to"]["exchange_name"], content=send_msg)

def exit_signal_handler(signum, frame):
   raise exit_signal("Exit signal %s received" % signum)

def handle_get_work(req_socket, reply, amqp_queue, known_items, broker_connection, msg_headers):
   """Retrieve a message from an AMQP queue and send it back to the
      requesting client"""
#   print "handle_get_work called " + str(time.localtime())

   # List of message headers that need special treatment
   special = ["Owner", "KillSig", "extra_args", "Iwd"]

   try:
      # Figure out the SlotID that is requesting work, and don't get any
      # more work if it is still processing work from a previous call
      slot = grep('^SlotID\s*=\s*(.+)$', reply.data)
      if slot == None:
         syslog.syslog(syslog.LOG_WARNING, "Unable to determine SlotID for request.")
      else:
         slot = slot[0]

      if known_items.known_slots.exists(slot) == True:
#         print "known slot %s" % slot
         reply.data = ""
         req_socket.send(pickle.dumps(reply,2))
         req_socket.shutdown(socket.SHUT_RD)
         req_socket.close()
         return

      # Get the work off the AMQP work queue if it exists
      try:
         received = amqp_queue.get(timeout=1)
         msg = received.content
         job_data = msg['application_headers']
      except Empty:
         reply.data = ""
         req_socket.send(pickle.dumps(reply,2))
         req_socket.shutdown(socket.SHUT_RD)
         req_socket.close()
         return

      if msg.properties.has_key('message_id') == False or msg['message_id'] == '':
         syslog.syslog(syslog.LOG_ERR, "Request does not have message_id, and is unusable.  Discarding")
         reply.data = ""
         reject_msg = msg
         reject_msg.body = "ERROR: Work Request does not have a unique message_id and was rejected."
         send_AMQP_response(broker_connection, received, reject_msg)
         received.complete()
      else:
         # Create the ClassAd to send to the requesting client
         msg_num = str(msg['message_id'])
         if job_data.has_key('Iwd') and str(job_data['Iwd']) != '':
            iwd = str(job_data['Iwd'])
         else:
            iwd = str("/tmp/condor_job." + str(os.getpid()))
         reply.data = "AMQPID = \"" + msg_num + "\"\n"
         reply.data += "WF_REQ_SLOT = \"" + slot + "\"\n"
         reply.data += "JobUniverse = 5\n"
#         reply.data += "JobLeaseDuration = 500000\n"
#         reply.data += "JobLeaseDuration = 3\n"
         reply.data += "IsFeatched = TRUE\n"
         reply.data += "Iwd = \"" + iwd + "\"\n"
         for field in [header for header in msg_headers.keys() if header not in special]:
            if job_data.has_key(field) == True and str(job_data[field]) != '':
               reply.data += field + " = \"" + str(job_data[field]) + "\"\n"
         if job_data.has_key('Owner') == True and str(job_data['Owner']) != '':
            reply.data += "Owner = \"" + str(job_data['Owner']) + "\"\n"
         else:
            reply.data += "Owner = \"nobody\"\n"
         if job_data.has_key('KillSig') == True and str(job_data['KillSig']) != '':
            reply.data += "KillSig = " + str(job_data['KillSig'])
         if job_data.has_key('extra_args') == True and str(job_data['extra_args']) != '':
            reply.data += str(job_data['extra_args'])

         # Preserve the message so we can ack it later
         known_items.AMQP_messages.add(msg_num, received)
   
         # Keep track of which slot is getting work so later we don't try
         # to get more for a slot that is still doing work
         known_items.known_slots.add(slot)

      # Send the work to the requesting client
      req_socket.send(pickle.dumps(reply,2))
      req_socket.shutdown(socket.SHUT_RD)
      req_socket.close()

   except exception_handler, error:
      for msg in error.msgs:
         syslog.syslog (error.level, msg)

def handle_reply_fetch(msg, known_items, broker_connection):
   """Send the data from a reply claim hook to a results AMQP queue.  Release
      the lock on the receiving AMQP queue in the case of a reject"""
#   print "handle_reply_fetch called " + str(time.localtime())
   # Find the AMQPID in the message received
   message_id = grep('^AMQPID\s*=\s*"(.+)"$', msg.data)
   if message_id == None:
      raise exception_handler(syslog.LOG_ERR, msg.data, "Unable to find AMQPID in exit message")
   else:
      message_id = message_id[0]

   if msg.type == condor_wf_types.reply_claim_reject:
      saved_msg = known_items.AMQP_messages.remove(message_id)
   else:
      saved_msg = known_items.AMQP_messages.get(message_id)

   if saved_msg == Empty:
      # Couldn't find the AMQP message that corresponds to the AMQPID
      # in the exit message.  This is bad and shouldn't happen.
      raise exception_handler(syslog.LOG_ERR, "Unable to find stored AMQP message with AMQPID %s." % message_id)
   else:
      # Place the data into the appropriate headers for the
      # results message.
      results = parse_data_into_AMQP_msg (msg.data)

      # Send the results to the appropriate exchange
      send_AMQP_response(broker_connection, saved_msg, results)

   if msg.type == condor_wf_types.reply_claim_reject:
      broker_connection.message_release([saved_msg.command_id, saved_msg.command_id])

def handle_prepare_job(req_socket, reply, known_items):
   """Prepare the environment for the job.  This includes extracting any
      archived data sent with the job request, as well as running a
      presetup script if one exists."""
#   print "handle_prepare_job called " + str(time.localtime())

   # Find the AMQPID in the message received
   message_id = grep('^AMQPID\s*=\s*"(.+)"$', reply.data)
   if message_id == None:
      raise exception_handler(syslog.LOG_ERR, reply.data, "Unable to find AMQPID in exit message")
   else:
      message_id = message_id[0]

   # Find the Current Working Directory  of the originating process
   # in the message received
   work_cwd = grep('^OriginatingCWD\s*=\s*"(.+)"$', reply.data)[0]

   saved_msg = known_items.AMQP_messages.get(message_id)
   if saved_msg == Empty:
      # Couldn't find the AMQP message that corresponds to the AMQPID
      # in the exit message.  This is bad and shouldn't happen.
      raise exception_handler(syslog.LOG_ERR, "Unable to find stored AMQP message with AMQPID %s" % message_id)
   else:
      # Place the body of the message, which should contain an archived
      # file, into the directory for the job
      reply.data = ""
      if saved_msg.content.body != '':
        # Write the archived file to disk
        input_filename = work_cwd + "/data.zip"
        input_file = open(input_filename, "wb")
        input_file.write(saved_msg.content.body)
        input_file.close()
        reply.data = "data.zip"

   # Send the information about the archive file to the requester
   req_socket.send(pickle.dumps(reply,2))
   req_socket.shutdown(socket.SHUT_RD)
   req_socket.close()

def handle_evict_claim(msg, known_items, broker_connection):
   """Send the evict claim information to a results AMQP queue."""
#   print "handle_evict_claim called " + str(time.localtime())
   # Find the AMQPID in the message received
   message_id = grep('^AMQPID\s*=\s*"(.+)"$', msg.data)
   if message_id == None:
      raise exception_handler(syslog.LOG_ERR, msg.data, "Unable to find AMQPID in exit message")
   else:
      message_id = message_id[0]

   saved_msg = known_items.AMQP_messages.remove(message_id)
   if saved_msg == Empty:
      # Couldn't find the AMQP message that corresponds to the AMQPID
      # in the exit message.  This is bad and shouldn't happen.
      raise exception_handler(syslog.LOG_ERR, "Unable to find stored AMQP message with AMQPID %s.  Message cannot be acknowledged!" % message_id)
   else:
      # Place the data into the appropriate headers for the
      # results message.
      results = parse_data_into_AMQP_msg (msg.data)

      # Send the results to the appropriate exchange
      send_AMQP_response(broker_connection, saved_msg, results)
      broker_connection.message_release([saved_msg.command_id, saved_msg.command_id])

def handle_update_job_status(msg, known_items, broker_connection):
   """Send the job status update information to a results AMQP queue."""
#   print "handle_update_job_status called " + str(time.localtime())

   # Find the AMQPID in the message received
   message_id = grep('^AMQPID\s*=\s*"(.+)"$', msg.data)
   if message_id == None:
      raise exception_handler(syslog.LOG_ERR, msg.data, "Unable to find AMQPID in exit message")
   else:
      message_id = message_id[0]

   saved_msg = known_items.AMQP_messages.get(message_id)
   if saved_msg == Empty:
      # Couldn't find the AMQP message that corresponds to the AMQPID
      # in the exit message.  This is bad and shouldn't happen.
      raise exception_handler(syslog.LOG_ERR, "Unable to find stored AMQP message with AMQPID %s" % message_id)
   else:
      # Place the data into the appropriate headers for the
      # results message.
      results = parse_data_into_AMQP_msg (msg.data)

      # Send the results to the appropriate exchange
      send_AMQP_response(broker_connection, saved_msg, results)

def handle_exit(req_socket, msg, known_items, broker_connection, msg_headers):
   """The job exited, so handle the reasoning appropriately.  If the
      job exited normally, then remove the work job from the AMQP queue,
      otherwise release the lock on the work.  Always place the results
      on the sender's reply-to AMQP queue"""
#   print "handle_exit called "  + str(time.localtime())

   try:
      # Determine the slot that is reporting results
      slot = grep ('^WF_REQ_SLOT\s*=\s*"(.+)"$', msg.data)
      if slot == None:
         syslog.syslog(syslog.LOG_WARNING, "Unable to determine SlotID for results.")
      else:
         # Remove the slot from the list of known slots, as it can now retrieve
         # more work.
         slot = slot[0]
         if known_items.known_slots.remove(slot) == Empty:
            syslog.syslog(syslog.LOG_WARNING, "Received exit message from unknown slot %s" % slot)

      # Find the AMQPID in the message we received
      message_id = grep('^AMQPID\s*=\s*"(.+)"$', msg.data)
      if message_id == None:
         raise exception_handler(syslog.LOG_ERR, msg.data, "Unable to find AMQPID in exit message")
      else:
         message_id = message_id[0]

      # Find the Current Working Directory  of the originating process
      # in the message received
      work_cwd = grep('^OriginatingCWD\s*=\s*"(.+)"$', msg.data)[0]

      # Place the data into the appropriate headers for the
      # results message.
      results = parse_data_into_AMQP_msg (msg.data)

      # Retrieve the AMQP message from the list of known messages so it
      # can be acknowledged or released
      ack_msg = known_items.AMQP_messages.get(message_id)
      if ack_msg == Empty:
         # Couldn't find the AMQP message that corresponds to the AMQPID
         # in the exit message.  This is bad and shouldn't happen.
         raise exception_handler(syslog.LOG_ERR, "Unable to find stored AMQP message with AMQPID %s.  Message cannot be acknowledged!" % message_id)
      else:
         # If any files were specified to be retrieved via the 'result_files'
         # field, then create an archive of the files (if they exist) and
         # place it in the body of the results message
         if ack_msg.content['application_headers'].has_key('result_files')  == True  and str(ack_msg.content['application_headers']['result_files']) != '':
            orig_cwd = os.getcwd()
            os.chdir(work_cwd)
            zip = zipfile.ZipFile("results.zip", "w")
            for result_file in ack_msg.content["application_headers"]["result_files"].split(' '):
               if os.path.exists(result_file) == True:
                  zip.write(result_file)
            zip.close()
            archived_file = open("results.zip", "rb")
            results.body = archived_file.read()
            archived_file.close()
            os.chdir(orig_cwd)

         # Send the results to the appropriate exchange
         send_AMQP_response(broker_connection, ack_msg, results)

         if msg.type == condor_wf_types.exit_exit:
            # Job exited normally, so grab the result files, transfer the
            # results to the specified AMQP reply-to queue, and ackowledge
            # the message on the AMQP work queue
#            print "Normal exit"

            # Acknowledge the message
            ack_msg.complete(cumulative=False)
            known_items.AMQP_messages.remove(message_id)
         else:
            # Job didn't exit normally, so release the lock for the message
#            print "Not normal exit: " + str(msg.type)
#            broker_connection.message_release(RangedSet(ack_msg.id))
            broker_connection.message_release([ack_msg.command_id, ack_msg.command_id])

      # Send acknowledgement to the originator that exit work is complete
      req_socket.send("Completed")
      req_socket.shutdown(socket.SHUT_RD)
      req_socket.close()
      return 0

   except exception_handler, error:
      for msg in error.msgs:
         syslog.syslog (error.level, msg)
         return 1

def main(argv=None):
   parser = ConfigParser.ConfigParser()
   broker = {}
   dest = "work_requests"
   AMQP_headers = {'Cmd': "", 'Arguments': "", 'Environment': "", 'Err': "",
                   'In': "", 'StarterUserLog': "",'StarterUserLogUseXML': "",
                   'Out': "", 'Iwd': "", 'Owner': "", 'KillSig': "",
                   'result_files': "", 'preconfigure_script': "",
                   'extra_args': ""}

   if argv is None:
      argv = sys.argv

   # Open a connection to the system logger
   syslog.openlog (os.path.basename(argv[0]))

   # Set signal handlers
   signal.signal(signal.SIGINT, exit_signal_handler)

   try:
      try:
         broker = read_config_file("Broker")
         server = read_config_file("AMQP_Module")
      except config_err, error:
         raise exception_handler(syslog.LOG_ERR, *(error.msg + ("Exiting.","")))

      # Create a container to share data between threads
      share_data = global_data()

      # Setup the AMQP connections
      client = Client(broker['ip'], int(broker['port']), qpid.spec.load(broker['spec']))
      client.start({"LOGIN": broker['user'], "PASSWORD": broker['password']})
      session = client.session()
      session.session_open()
      session.message_subscribe(queue=broker['queue'], destination=dest, confirm_mode = 1)
      session.message_flow(dest, 0, 0xFFFFFFFF)
      session.message_flow(dest, 1, 0xFFFFFFFF)
      work_queue = client.queue(dest)

      # Setup the socket for communication with condor
      listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      try:
         listen_socket.bind((server['ip'], int(server['port'])))
         listen_socket.listen(int(server['queued_connections']))
      except socket.error, error:
         raise exception_handler(syslog.LOG_ERR, "Failed to listen on %s:%s" % (server['ip'], server['port']))

      # Accept all incoming connections and act accordingly
      while True:
         sock,address = listen_socket.accept()
         recv_data = socket_read_all(sock)
         condor_msg = pickle.loads(recv_data)

         # Set up a child thread to perform the desired action
         if condor_msg.type == condor_wf_types.get_work:
            child = threading.Thread(target=handle_get_work, args=(sock, condor_msg, work_queue, share_data, session, AMQP_headers))
         elif condor_msg.type == condor_wf_types.reply_claim_accept or \
              condor_msg.type == condor_wf_types.reply_claim_reject:
            child = threading.Thread(target=handle_reply_fetch, args=(condor_msg, share_data, session))
         elif condor_msg.type == condor_wf_types.prepare_job:
            child = threading.Thread(target=handle_prepare_job, args=(sock, condor_msg, share_data))
#         elif condor_msg.type == condor_wf_types.evict_claim:
#            child = threading.Thread(target=handle_evict_claim, args=(condor_msg, share_data, session))
         elif condor_msg.type == condor_wf_types.update_job_status:
            child = threading.Thread(target=handle_update_job_status, args=(condor_msg, share_data, session))
         elif condor_msg.type == condor_wf_types.exit_exit or \
              condor_msg.type == condor_wf_types.exit_remove or \
              condor_msg.type == condor_wf_types.exit_hold or \
              condor_msg.type == condor_wf_types.exit_evict:
            child = threading.Thread(target=handle_exit, args=(sock, condor_msg, share_data, session, AMQP_headers))
         else:
            print "Unknown type"
         child.setDaemon(True)
         child.start()

   except exit_signal, exit_data:
      # Close the session before exiting
      listen_socket.shutdown(socket.SHUT_RD)
      listen_socket.close()
      session.session_close()
      return 0

   except exception_handler, error:
      for msg in error.msgs:
         if (msg != ''):
            syslog.syslog(error.level, msg)
      return 1

if __name__ == "__main__":
    sys.exit(main())
