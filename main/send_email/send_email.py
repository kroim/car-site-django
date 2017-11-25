import httplib2
import os
import oauth2client
from oauth2client import client, tools
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from apiclient import errors, discovery
import mimetypes
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from django.contrib.auth.models import User


SCOPES = 'https://www.googleapis.com/auth/gmail.send'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Gmail API Python Send Email'

def get_credentials():
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'gmail-python-email-send.json')
    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        credentials = tools.run_flow(flow, store)
        print 'Storing credentials to ' + credential_path
    return credentials

def SendMessage(sender, to, subject, msgHtml, msgPlain, attachmentFile=None):
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('gmail', 'v1', http=http)
    message1 = CreateMessageHtml(sender, to, subject, msgHtml, msgPlain)
    result = SendMessageInternal(service, "me", message1)
    return result

def SendMessageInternal(service, user_id, message):
    try:
        message = (service.users().messages().send(userId=user_id, body=message).execute())
        print 'Message Id: %s' % message['id']
        return message
    except errors.HttpError, error:
        print 'An error occurred: %s' % error
        return "Error"
    return "OK"

def CreateMessageHtml(sender, to, subject, msgHtml, msgPlain):
    msg = MIMEMultipart('alternative') 
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = to

    msg.attach(MIMEText(msgPlain, 'plain'))
    msg.attach(MIMEText(msgHtml, 'html'))
    return {'raw': base64.urlsafe_b64encode(msg.as_string())}


#Drive function
def compile_and_send_email(user_id, car_id):

    user = User.objects.get(id=user_id)
    car = Car.objects.get(id=car_id)

    f_name = user.first_name
    l_namne = user.last_name
    c_email = user.username
    city = car.stock_number[:2]
    year = car.year
    make = car.make
    model = car.model
    trim = car.trim

    image_data = open('carboi_logo.png','rb').read()
    html_part = MIMEMultipart(_subtype='related')
    body = MIMEText('<!DOCTYPE html><html><body>\
    <a href="carboi.com"><img src="cid:myimage" style="width:508px;height:94px;border:0"/></a>\
<div>Hello {},\
    <p>Hope all is well and thank you for considering Carboi.com for your new car purchase! I received your request about our {} {} {} {}\
    and have attached 6 good deals for you to below that matches your search criteria.</p>\
    <p>All of our cars are Certified, Pre-Owned, Pre-Screened,\
    and are still under bumper-to-bumper manufacturer\
    warranty, so rest assured that you will be getting a very clean and well-maintained car. To top it all off,\
    we can deliver that perfect of a car and still offer the lowest price on the market!</p>\
    <p>Please see your listing below: (note that some of the pictures are photos from the warehouse and taken prior to our awesome reconditioning and detailing process)\
    </p></div><div>\
  <div><b>1. Listing : </b><a href="google.com">{} {} {}</a></div>\
  <div><b>2. Listing : </b><a href="google.com">{} {} {}</a></div>\
  <div><b>3. Listing : </b><a href="google.com">{} {} {}</a></div>\
  <div><b>4. Listing : </b><a href="google.com">{} {} {}</a></div>\
  <div><b>5. Listing : </b><a href="google.com">{} {} {}</a></div>\
  <div><b>6. Listing : </b><a href="google.com">{} {} {}</a></div>\
</div>\
<div>\
<p>SEE EVEN MORE {} {} {} {} HERE</p>\
<p>What do you think? Let me know which one you like and I can  send you a copy of out <b>152 point Certified inspection</b> report.</p>\
<p>You can reach me directly at 408-313-3786 with any questions or to secure any of our cars!</p>\
<p>Look forward to hearing from you soon.</p>\
<p>--Happy Car Buying!</p>\
<p>Cheers,</p>\
<p>Shaun Boland\
<div>Carboi Car Expert</div>\
<div>O. 855-966-6694</div>\
<div>C. 408-313-4786</div>\
<div>www.carboi.com</div></p></div></body></html>'.format(f_name,
                                                            year,make,model,trim,
                                                            make,model,trim,
                                                            make,model,trim,
                                                            make,model,trim,
                                                            make,model,trim,
                                                            make,model,trim,
                                                            make,model,trim,
                                                            year,make,model,trim,),_subtype='html')
    html_part.attach(body)
    img = MIMEImage(image_data,'png')
    img.add_header('Content-Id','<myimage>')
    img.add_header('Content-Disposition', 'inline',filename='myimage')
    
    #format email
    html_part.attach(img)
    to = 'joshua.steubs@gmail.com'
    sender = 'joshua.steubs@gmail.com'
    subject = 'CarGurus Customer Lead'
    msgPlain = ''
    html_part['to'] = 'joshua.steubs@gmail.com'

    #credentials
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('gmail', 'v1', http=http)
    
    message1 = {'raw': base64.urlsafe_b64encode(html_part.as_string())}
    
    result = SendMessageInternal(service, "me", message1)


compile_and_send_email(14,42399)