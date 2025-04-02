#!/bin/python3
import Milter
import os
import time
import sys
from Milter.utils import parse_addr
import redis
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Global Configuration
MAX_EMAILS_PER_5_MINUTES = int(os.getenv("MAX_EMAILS_PER_5_MINUTES", 50)) # Max emails per 5 minutes
MAX_EMAILS_PER_HR = int(os.getenv("MAX_EMAILS_PER_HR", 100)) # Max emails per hour
MAX_CC_RECIPIENTS = int(os.getenv("MAX_CC_RECIPIENTS", 15)) # Max CC recipients per mail
MAX_EMAIL_SINGLE = int(os.getenv("MAX_EMAIL_SINGLE", 5)) # Max email recipients per mail
SOCKET_HOST = os.getenv("SOCKET_HOST", "localhost") # Milter socket host
SOCKET_PORT = os.getenv("SOCKET_PORT", "10032") # Milter socket port


@Milter.rejected_recipients
class MailMilter(Milter.Milter):

  # Class-level Redis connection (shared across all instances)
  redis = None  

  # Initialize Redis connection
  @classmethod
  def init_redis(cls): # This method is called only once
      if cls.redis is None:  # Ensure only one connection is created
          cls.redis = redis.Redis(
              host=os.getenv("REDIS_HOST", "localhost"),
              port=int(os.getenv("REDIS_PORT", 6379)),
              password=os.getenv("REDIS_PASSWORD", None),
              decode_responses=True
          )
          try:
              cls.redis.ping()
              print("Redis Connected.")
          except redis.ConnectionError as e:
              print("Redis Connection Failed:", e)
              sys.exit(1)  # Exit if Redis is unavailable

  def __init__(self):  # A new instance with each new connection.
    print("\n----------- Started -----------")
    super().__init__()
    self.cc_count = 0 # CC count
    self.mail_count_per_hr = 0 # Mail count per hour
    self.mail_count_per_5_min = 0 # Mail count per 5 minutes
    self.totalTo = set() # List of all recipients
    self.mailFromAddr = "" # Sender email address
    self.MAX_EMAILS_PER_5_MINUTES = MAX_EMAILS_PER_5_MINUTES # Max emails per 5 minutes
    self.MAX_EMAILS_PER_HR = MAX_EMAILS_PER_HR # Max emails per hour
    self.MAX_CC_RECIPIENTS = MAX_CC_RECIPIENTS # Max CC recipients per mail
    self.MAX_EMAIL_SINGLE = MAX_EMAIL_SINGLE # Max email recipients per mail

    # Ensure Redis is initialized
    self.init_redis()

    # Initialize Redis inside the instance
    self.redis = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        password=os.getenv("REDIS_PASSWORD", None),
        decode_responses=True
    )

  # Checking outgoing number of mail per user
  def outgoingMailValidation(self):
    try:

      totalTo = int(len(self.totalTo)) - self.cc_count

      print("totalTo: ", totalTo)

      if totalTo > self.MAX_EMAIL_SINGLE:
        self.setreply('550','5.7.1', 'Too many recipient address in a single email. Limit is ' + str(self.MAX_EMAIL_SINGLE) + '.')
        return False

      if self.cc_count > self.MAX_CC_RECIPIENTS:
        self.setreply('550','5.7.1', 'Too many CC recipients for the email. Limit is ' + str(self.MAX_CC_RECIPIENTS) + '.')
        return False

      if totalTo > self.MAX_EMAILS_PER_HR:
        self.setreply('550','5.7.1','Number of email per hour is exceeded. ( Limit: ' + str(self.MAX_EMAILS_PER_HR) + ', Trying To Send: ' + str(totalTo) + ' )')
        return False

      if totalTo > self.MAX_EMAILS_PER_5_MINUTES:
        self.setreply('550','5.7.1','Number of email per 5 minute is exceeded. ( Limit: ' + str(self.MAX_EMAILS_PER_5_MINUTES) + ', Trying To Send: ' + str(totalTo) + ' )')
        return False

      print("totalTo: ",totalTo)
      redisKey = self.fromUser + "_" + self.fromDomain
      mailDetails = self.redis.hgetall(redisKey)
      currentTime = time.time()
      if mailDetails is None or mailDetails.get('limit5MinTimestamp', None) is None:
        print("No of outgoing mail: ", totalTo, ",limit: ", self.MAX_EMAILS_PER_HR)
        self.redis.hset(redisKey, mapping={'noOfMailTotal': totalTo, 'noOfMailIn5Min': totalTo, 'limit5MinTimestamp':currentTime })
        self.redis.expire(redisKey, 3600)
        return True

      # Retrieve No Of Mail Total Send
      noOfMailTotal =  mailDetails.get('noOfMailTotal', None)
      if noOfMailTotal:
          noOfMailTotal = int(noOfMailTotal)
          print(f'No Of Mail Total: {noOfMailTotal}')
      else:
          noOfMailTotal = 0

      # Retrieve No Of Mail Total Mail Send In 5 Minute
      noOfMailIn5Min =  mailDetails.get('noOfMailIn5Min', None)
      if noOfMailIn5Min:
          noOfMailIn5Min = int(noOfMailIn5Min)
          print(f'No Of Mail In 5Min: {noOfMailIn5Min}')
      else:
          noOfMailIn5Min = 0

      # Retrieve Timestamp To Check 5 Minute
      limit5MinTimestamp =  mailDetails.get('limit5MinTimestamp', None)
      if not limit5MinTimestamp:
          limit5MinTimestamp = None

      print("totalTo: ", totalTo)

      # Checking 5minute limit
      if limit5MinTimestamp is not None:
        time_difference_in_seconds = time.time() - float(limit5MinTimestamp)
        time_difference_in_minutes = time_difference_in_seconds / 60
        print("time_difference_in_minutes: ", int(time_difference_in_minutes))
        if(int(time_difference_in_minutes) <= 5):
          if noOfMailIn5Min < int(self.MAX_EMAILS_PER_5_MINUTES):
            self.redis.hset(redisKey, 'noOfMailIn5Min', noOfMailIn5Min + 1)
            print("No of outgoing mail in 5 minute: ", noOfMailIn5Min + 1, ", limit: ", self.MAX_EMAILS_PER_5_MINUTES)
          else:
            self.setreply('550','5.7.1','Number of email per 5 minute is exceeded. ( '+ 'Total Send: '+ str(noOfMailIn5Min) + ', Limit: ' +str(self.MAX_EMAILS_PER_5_MINUTES) + ', Trying To Send: ' + str(totalTo) + ' )')
            return False
        else:
          self.redis.hset(redisKey, 'noOfMailIn5Min', 1)
          self.redis.hset(redisKey, 'limit5MinTimestamp', currentTime)
        #

      # Checking 1hr limit
      if noOfMailTotal <= int(self.MAX_EMAILS_PER_HR) and int(totalTo) <= int(self.MAX_EMAILS_PER_HR):
        self.redis.hset(redisKey, 'noOfMailTotal', noOfMailTotal + 1)
        print("No of outgoing mail: ", noOfMailTotal + 1, ",limit: ", self.MAX_EMAILS_PER_HR)
      else:
        self.setreply('550','5.7.1','Number of email per hour is exceeded. ( '+ 'Total Send: '+ str(noOfMailTotal) + ', Limit: ' + str(self.MAX_EMAILS_PER_HR) + ', Trying To Send: ' + str(totalTo) + ' )')
        return False
      #

      print("Expire redis key at ", self.redis.ttl(redisKey))

      return True
    except Exception as e:
      print(time.strftime('%Y-%b-%d %H:%M:%S '), " No of outgoing mail Error: ", e)
      return True


  @Milter.noreply
  def connect(self, IPname, family, hostaddr):
    return Milter.CONTINUE

  def hello(self, heloname):
    return Milter.CONTINUE

  def envfrom(self, mailfrom, *str):
    self.F = mailfrom
    self.fromUser = parse_addr(mailfrom)[0]
    self.fromDomain= parse_addr(mailfrom)[1]
    self.mailFromAddr = self.fromUser + "@" +self.fromDomain
    print("Mail From: ", self.mailFromAddr)
    return Milter.CONTINUE

  def envrcpt(self, to, *str):
    try:
      rcptinfo = to,Milter.dictfromlist(str)
      self.R = []
      self.R.append(rcptinfo)
      self.toUser = parse_addr(to)[0]
      self.toDomain= parse_addr(to)[1]
      self.mailToAddr = self.toUser + "@" +self.toDomain
      print("Mail To: ", self.mailToAddr)
      self.totalTo.add(self.mailToAddr)
      return Milter.CONTINUE
    except Exception as e:
       print(time.strftime('%Y-%b-%d %H:%M:%S '), " envrcpt Error: ", e)
       return Milter.CONTINUE

  def header(self,field,value):
    try:
      if field.lower() == 'cc':
          self.cc_count += len(value.split(','))
      return Milter.CONTINUE
    except Exception as e:
       print(time.strftime('%Y-%b-%d %H:%M:%S '), " header Error: ", e)
       return Milter.CONTINUE


  def eoh(self):
    try:
      # if self.fromDomain in sendersList:
      validate = self.outgoingMailValidation()
      print("Validate: " , validate)
      if not validate:
        return Milter.REJECT
      return Milter.CONTINUE
    except Exception as e:
       print(time.strftime('%Y-%b-%d %H:%M:%S '), " EOH Error: ", e)
       return Milter.CONTINUE

  @Milter.noreply
  def body(self, chunk):
    try:
      return Milter.CONTINUE
    except Exception as e:
       print(time.strftime('%Y-%b-%d %H:%M:%S '), " eom Error: ", e)
       return Milter.CONTINUE


  def close(self):
    print("----------- Exited -----------\n")
    return Milter.CONTINUE

  def abort(self):
    # client disconnected prematurely
    print("Aborted")
    return Milter.CONTINUE

def main():

  # Setting up the Milter
  socketAddr = 'inet:'+SOCKET_PORT+'@'+SOCKET_HOST
  timeout = 600
  print("Socket Address: ", socketAddr)

  Milter.setdbg(1)
  Milter.getdiag()
  # Register to have the Milter factory create instances of your class:
  Milter.factory = MailMilter
  # Set the flags for the Milter
  flags = Milter.CHGHDRS + Milter.ADDHDRS
  Milter.set_flags(flags)
  print("%s Mail Throttle Validation milter startup" % time.strftime('%Y %b %d %H:%M:%S'))
  sys.stdout.flush()
  # Run the Milter
  Milter.runmilter("MailMilter",socketAddr,timeout)
  print("%s Mail Throttle Validation Milter shutdown" % time.strftime('%Y %b %d %H:%M:%S'))

if __name__ == "__main__":

  main()