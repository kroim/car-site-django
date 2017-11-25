from django.conf import settings
from django.contrib.auth.models import User

from django_common.helper import send_mail
from django_cron import CronJobBase, Schedule
import os
import smtplib
import time
import re
import imaplib
import email
from email.utils import parseaddr
from zopy.crm import CRM
import json

ORG_EMAIL = "@gmail.com"
FROM_EMAIL = "longhongwang" + ORG_EMAIL
FROM_PWD = "!@#456gmail"
SMTP_SERVER = "imap.gmail.com"


def dump(obj):
    for attr in dir(obj):
        print("obj.%s = %s" % (attr, getattr(obj, attr)))

class EmailUsercountCronJob(CronJobBase):
    """
    Send an email with the user count.
    """
    RUN_EVERY_MINS = 1

    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'cron.EmailUsercountCronJob'



    def do(self):
        message = 'Entering to read mails:'
        print(message)

        try:
            mail = imaplib.IMAP4_SSL(SMTP_SERVER)
            mail.login(FROM_EMAIL, FROM_PWD)
            mail.select('inbox')

            type, data = mail.search(None, 'ALL')
            mail_ids = data[0]

            id_list = mail_ids.split()
            first_email_id = int(id_list[0])
            latest_email_id = int(id_list[-1])

            for i in range(latest_email_id, first_email_id, -1):
                typ, data = mail.fetch(i, '(RFC822)')

                for response_part in data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_string(response_part[1])
                        email_from = msg['from']
                        retParse = parseaddr(email_from)
                        print retParse[1]
                        print msg['subject']
                        #user = User.objects.create_user(username=retParse[1], password='1', first_name='hello', last_name='test')
                        #user.account.phone = '123456'
                        #user.save

                        authToken = "d441952ae23eeef0fc25238ee73b331f"
                        crm = CRM(authToken=authToken, scope="ZohoCRM/crmapi")
                        #crm_search = crm.searchRecords(module="CustomModule3",criteria={"Correo Electronico": "carboi408@gmail.com"})
                        #print crm_search.result.CustomModule3.row.FL.custommodule3_id

                        xmlData = '<row no="1"><FL val="Lead Source">Web Download</FL><FL val="Company">Your Company</FL><FL val="First Name">Hannah</FL><FL val="Last Name">Smith</FL>' \
                                  '<FL val="Email">testing@testing.com</FL><FL val="Title">Manager</FL><FL val="Phone">1234567890</FL><FL val="Home Phone">0987654321</FL>' \
                                  '<FL val="Other Phone">1212211212</FL><FL val="Fax">02927272626</FL><FL val="Mobile">292827622</FL></row>'

                        crm_insert = crm.insertRecords(module="Leads", xmlData=[xmlData], version=4,  duplicateCheck=2)

                        print crm_insert.result.recorddetail.FL.id
                        #print dump(crm_insert.result)
                        #print crm_insert
                        #print crm
                break

        except Exception, e:
            print str(e)
