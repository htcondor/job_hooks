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
#from qpid.client import Client
#from qpid.content import Content
from qpid.util import connect
from qpid.connection import Connection
from qpid.datatypes import Message, RangedSet, uuid4
from qpid.queue import Empty

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

   def items(self):
      """Return the (key,value) pairs stored in the dictionary"""
      self.__lock__()
      list = self.__list__.items()
      self.__unlock__()
      return list

   def keys(self):
      """Return the keys in the dictionary"""
      self.__lock__()
      list = self.__list__.keys()
      self.__unlock__()
      return list

   def values(self):
      """Return the values stored in the dictionary"""
      self.__lock__()
      list = self.__list__.values()
      self.__unlock__()
      return list

class work_data(object):
   def __init__(self, msg, slot_num, time):
      self.__AMQP_msg__ = msg
      self.__slot__ = slot_num
      self.__access_time__ = time

   def set_AMQP_msg(self, msg):
      self.__AMQP_msg__ = msg

   def get_AMQP_msg(self):
      return self.__AMQP_msg__

   AMQP_msg = property(get_AMQP_msg, set_AMQP_msg)

   def set_slot(self, slot_num):
      self.__slot__ = slot_num

   def get_slot(self):
      return self.__slot__

   slot = property(get_slot, set_slot)

   def set_access_time(self, time):
      self.__access_time__ = time

   def get_access_time(self):
      return self.__access_time__

   access_time = property(get_access_time, set_access_time)

class global_data(object):
   def __init__(self):
      self.__work_list__ = threadsafe_dict()
      self.__max_lease__ = 0

   def set_max_lease_time(self, time):
      self.__max_lease__ = float(time)

   def get_max_lease_time(self):
      return self.__max_lease__

   max_lease = property(get_max_lease_time, set_max_lease_time)

   def add_work(self, key, AMQP_msg, slot, time):
      """Add work information to list of known work items"""
      self.__work_list__.add(key, work_data(AMQP_msg, slot, time))

   def remove_work(self, key):
      """Remove work information from the list of known work items and
         return the work removed.  If the work with the specified key
         doesn't exist, Empty is returned"""
      return self.__work_list__.remove(key)

   def get_work(self, key):
      """Get work information from the list of known work items.  If the
         work with the given key doesn't exist, Empty is returned"""
      return self.__work_list__.get(key)

   def slot_in_use(self, slot_num):
      """Returns True if the given slot is currently processing work,
         False otherwise"""
      for work in self.__work_list__.values():
         if work.slot == slot_num:
            return True
      return False

   def values(self):
      """Returns a list of work_data objects which contains all known
         work information"""
      return self.__work_list__.values()

def lease_monitor(msg_list, max_lease_time, interval, broker_connection):
   """Monitor all work for lease expiration.  If a lease expired, the work
      is released"""
   while True:
#      print "Checking leases " + str(time.time())
      expire_time = float(time.time())
      for item in msg_list.values():
#         print "access time = " + str(item.access_time)
#         print "expire time = " + str(expire_time)
         if (float(item.access_time) + float(max_lease_time)) < expire_time:
            # The lease for this message has expired, so delete it from the
            # list of known messages and release the lock
#            print "Expiring " + item.AMQP_msg.content['message_id']
            msg_list.remove_work(item.AMQP_msg.message_id)
#            broker_connection.message_release([item.AMQP_msg.command_id, item.AMQP_msg.command_id])
            broker_connection.message_release(RangedSet(item.AMQP_msg.id))
      time.sleep(int(interval))

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

def parse_data_into_AMQP_headers(data, session):
   """Takes a set of data and parses it into the application_headers in an
      AMQP message property.  Returns the message property with the headers
      filled in."""
   headers = {}
#   msg =Content(properties={'application_headers':{}})
   for line in data.split('\n'):
      found = grep('^(.+)\s*=\s*(.*)$', line)
      if found != None:
         headers[found[0]] = found[1]
   return session.message_properties(application_headers=headers)

def send_AMQP_response(connection, orig_req, msg_properties, data=None):
   """Sends send_msg to the reply_to queue in orig_req using the broker
      connection 'connection'"""
   reply_to = orig_req.get("message_properties").reply_to
   delivery_props = connection.delivery_properties(routing_key=reply_to["routing_key"])
#   send_msg["routing_key"] = orig_req.content["reply_to"]["routing_key"]
#   connection.message_transfer(destination=orig_req.content["reply_to"]["exchange_name"], content=send_msg)
   connection.message_transfer(destination=reply_to["exchange"], message=Message(msg_properties, delivery_props, data))

def exit_signal_handler(signum, frame):
   raise exit_signal("Exit signal %s received" % signum)

def handle_get_work(req_socket, reply, amqp_queue, known_items, broker_connection):
   """Retrieve a message from an AMQP queue and send it back to the
      requesting client"""
#   print "handle_get_work called " + str(time.localtime())

   # List of message headers that need special treatment
   special = ["Owner"]

   try:
      # Figure out the SlotID that is requesting work, and don't get any
      # more work if it is still processing work from a previous call
      slot = grep('^SlotID\s*=\s*(.+)$', reply.data)
      if slot == None:
         syslog.syslog(syslog.LOG_WARNING, "Unable to determine SlotID for request.")
      else:
         slot = slot[0]

      if known_items.slot_in_use(slot) == True:
#         print "known slot %s" % slot
         reply.data = ""
         req_socket.send(pickle.dumps(reply,2))
         req_socket.shutdown(socket.SHUT_RD)
         req_socket.close()
         return

      # Get the work off the AMQP work queue if it exists
      try:
#         received = amqp_queue.get(timeout=1)
         msg = amqp_queue.get(timeout=1)
#         msg = received.content
         job_data = msg.get('message_properties').application_headers
      except Empty:
         reply.data = ""
         req_socket.send(pickle.dumps(reply,2))
         req_socket.shutdown(socket.SHUT_RD)
         req_socket.close()
         return

#      print msg
#      if msg.properties.has_key('message_id') == False or msg['message_id'] == '':
      if msg.get('message_properties').message_id == '':
# FIX ME
         syslog.syslog(syslog.LOG_ERR, "Request does not have message_id, and is unusable.  Discarding")
         reply.data = ""
         reject_msg = msg
         reject_msg.body = "ERROR: Work Request does not have a unique message_id and was rejected."
         send_AMQP_response(broker_connection, msg, reject_msg)
         session.message_accept(RangedSet(msg.id))
#      elif msg.properties.has_key('expiration') == True and msg['expiration'] > time.time():
#      elif msg.expiration > time.time():
#         print "Message has expired and shouldn't be processed"
      else:
         # Create the ClassAd to send to the requesting client
         msg_num = str(msg.get('message_properties').message_id)
         reply.data = "AMQPID = \"" + msg_num + "\"\n"
         reply.data += "WF_REQ_SLOT = \"" + slot + "\"\n"
         reply.data += "JobUniverse = 5\n"
#         reply.data += "JobLeaseDuration = 500000\n"
#         reply.data += "JobLeaseDuration = 3\n"
         reply.data += "IsFeatched = TRUE\n"
         for field in [header for header in job_data.keys() if header not in special]:
            reply.data += field + " = " + str(job_data[field]) + "\n"
         if job_data.has_key('Owner') == True and str(job_data['Owner']) != '':
            reply.data += "Owner = " + str(job_data['Owner']) + "\n"
         else:
            reply.data += "Owner = \"nobody\"\n"

         # Preserve the work data was processed so it can be
         # acknowledged, expired, or released as needed
         known_items.add_work(msg_num, msg, slot, time.time())
   
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
      saved_work = known_items.remove_work(message_id)
   else:
      saved_work = known_items.get_work(message_id)

   if saved_work == Empty:
      # Couldn't find the AMQP message that corresponds to the AMQPID
      # in the exit message.  This is bad and shouldn't happen.
      raise exception_handler(syslog.LOG_ERR, "Unable to find stored AMQP message with AMQPID %s." % message_id)
   else:
      # Place the data into the appropriate headers for the
      # results message.
      msg_props = parse_data_into_AMQP_headers(msg.data, broker_connection)

      # Send the results to the appropriate exchange
      send_AMQP_response(broker_connection, saved_work.AMQP_msg, msg_props)

   if msg.type == condor_wf_types.reply_claim_reject:
#      broker_connection.message_release([saved_work.AMQP_msg.command_id, saved_work.AMQP_msg.command_id])
      broker_connection.message_release(RangedSet(saved_work.AMQP_msg.id))
#      print "Work rejected"

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

   saved_work = known_items.get_work(message_id)
   if saved_work == Empty:
      # Couldn't find the AMQP message that corresponds to the AMQPID
      # in the exit message.  This is bad and shouldn't happen.
      raise exception_handler(syslog.LOG_ERR, "Unable to find stored AMQP message with AMQPID %s" % message_id)
   else:
      # Update the access time so the job isn't expired
      saved_work.access_time = time.time()

      # Place the body of the message, which should contain an archived
      # file, into the directory for the job
      reply.data = ""
      if saved_work.AMQP_msg.body != '':
        # Write the archived file to disk
        input_filename = work_cwd + "/data.zip"
        input_file = open(input_filename, "wb")
        input_file.write(saved_work.AMQP_msg.body)
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

   saved_work = known_items.remove_work(message_id)
   if saved_work == Empty:
      # Couldn't find the AMQP message that corresponds to the AMQPID
      # in the exit message.  This is bad and shouldn't happen.
      raise exception_handler(syslog.LOG_ERR, "Unable to find stored AMQP message with AMQPID %s." % message_id)
   else:
      # Place the data into the appropriate headers for the
      # results message.
      msg_props = parse_data_into_AMQP_headers(msg.data, broker_connection)

      # Send the results to the appropriate exchange
      send_AMQP_response(broker_connection, saved_work.AMQP_msg, msg_props)
#      broker_connection.message_release([saved_work.AMQP_msg.command_id, saved_work.AMQP_msg.command_id])
      broker_connection.message_release(RangedSet(saved_work.AMQP_msg.id))

def handle_update_job_status(msg, known_items, broker_connection):
   """Send the job status update information to a results AMQP queue."""
#   print "handle_update_job_status called " + str(time.localtime())

   # Find the AMQPID in the message received
   message_id = grep('^AMQPID\s*=\s*"(.+)"$', msg.data)
   if message_id == None:
      raise exception_handler(syslog.LOG_ERR, msg.data, "Unable to find AMQPID in exit message")
   else:
      message_id = message_id[0]

   saved_work = known_items.get_work(message_id)
   if saved_work == Empty:
      # Couldn't find the AMQP message that corresponds to the AMQPID
      # in the exit message.  This is bad and shouldn't happen.
      raise exception_handler(syslog.LOG_ERR, "Unable to find stored AMQP message with AMQPID %s" % message_id)
   else:
      # Update the access time so the job isn't expired
      saved_work.access_time = time.time()

      # Place the data into the appropriate headers for the
      # results message.
      msg_props = parse_data_into_AMQP_headers(msg.data, broker_connection)

      # Send the results to the appropriate exchange
      send_AMQP_response(broker_connection, saved_work.AMQP_msg, msg_props)

def handle_exit(req_socket, msg, known_items, broker_connection):
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
         # Verify the slot sending results is known to be in use.  If not,
         # somehow results have been send from an unknown slot.
         slot = slot[0]
         if known_items.slot_in_use(slot) == False:
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
      msg_props = parse_data_into_AMQP_headers(msg.data, broker_connection)

      # Retrieve the AMQP message from the list of known messages so it
      # can be acknowledged or released
      saved_work = known_items.remove_work(message_id)
      if saved_work == Empty:
         # Couldn't find the AMQP message that corresponds to the AMQPID
         # in the exit message.  This is bad and shouldn't happen.
         raise exception_handler(syslog.LOG_ERR, "Unable to find stored AMQP message with AMQPID %s.  Message cannot be acknowledged!" % message_id)
      else:
         # Update the access time so the job isn't expired
         saved_work.access_time = time.time()

         # If any files were specified to be retrieved via the 'result_files'
         # field, then create an archive of the files (if they exist) and
         # place it in the body of the results message
         ack_msg = saved_work.AMQP_msg
         app_hdrs = ack_msg.get('message_properties').application_headers
         data = ""
         if app_hdrs.has_key('result_files')  == True and str(app_hdrs['result_files']) != '':
            orig_cwd = os.getcwd()
            os.chdir(work_cwd)
            zip = zipfile.ZipFile('results.zip', 'w')
            for result_file in app_hdrs['result_files'].split(' '):
               if os.path.exists(result_file) == True:
                  zip.write(result_file)
            zip.close()
            archived_file = open('results.zip', 'rb')
            data = archived_file.read()
            archived_file.close()
            os.chdir(orig_cwd)

         # Send the results to the appropriate exchange
         send_AMQP_response(broker_connection, ack_msg, msg_props, data)

         if msg.type == condor_wf_types.exit_exit:
            # Job exited normally, so grab the result files, transfer the
            # results to the specified AMQP reply-to queue, and ackowledge
            # the message on the AMQP work queue
#            print "Normal exit"

            # Acknowledge the message
            broker_connection.message_accept(RangedSet(ack_msg.id))
#            ack_msg.complete(cumulative=False)
         else:
            # Job didn't exit normally, so release the lock for the message
#            print "Not normal exit: " + str(msg.type)
            broker_connection.message_release(RangedSet(ack_msg.id))
#            broker_connection.message_release([ack_msg.command_id, ack_msg.command_id])

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
#      client = Client(broker['ip'], int(broker['port']), qpid.spec.load(broker['spec']))
#      client.start({'LOGIN': broker['user'], 'PASSWORD': broker['password']})
      server_socket = connect(broker['ip'], int(broker['port']))
      connection = Connection(sock=server_socket)
      connection.start()
      session = connection.session(str(uuid4()))
#      session.session_open()
      session.message_subscribe(queue=broker['queue'], destination=dest, accept_mode=session.accept_mode.explicit)
      session.message_flow(dest, 0, 0xFFFFFFFF)
      session.message_flow(dest, 1, 0xFFFFFFFF)
      work_queue = session.incoming(dest)

      # Create a thread to monitor work expiration times
      monitor_thread = threading.Thread(target=lease_monitor, args=(share_data, server['lease_time'], server['lease_check_interval'], session))
      monitor_thread.setDaemon(True)
      monitor_thread.start()

      # Setup the socket for communication with condor
      listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      try:
         listen_socket.bind((server['ip'], int(server['port'])))
         listen_socket.listen(int(server['queued_connections']))
      except socket.error, error:
         raise exception_handler(syslog.LOG_ERR, 'Failed to listen on %s:%s' % (server['ip'], server['port']))

      # Accept all incoming connections and act accordingly
      while True:
         sock,address = listen_socket.accept()
         recv_data = socket_read_all(sock)
         condor_msg = pickle.loads(recv_data)

         # Set up a child thread to perform the desired action
         if condor_msg.type == condor_wf_types.get_work:
            child = threading.Thread(target=handle_get_work, args=(sock, condor_msg, work_queue, share_data, session))
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
            child = threading.Thread(target=handle_exit, args=(sock, condor_msg, share_data, session))
         else:
            print 'Unknown type'
         child.setDaemon(True)
         child.start()

   except exit_signal, exit_data:
      # Close the session before exiting
      listen_socket.shutdown(socket.SHUT_RD)
      listen_socket.close()
      session.close(timeout=10)
      return 0

   except exception_handler, error:
      for msg in error.msgs:
         if (msg != ''):
            syslog.syslog(error.level, msg)
      return 1

if __name__ == '__main__':
    sys.exit(main())
