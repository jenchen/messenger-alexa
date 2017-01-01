from flask import Flask, request, render_template, json, current_app
from flask_ask import Ask, statement, question, logger, session
import logging
import boto3

logging.getLogger("flask_ask").setLevel(logging.DEBUG)

app = Flask(__name__)
ask = Ask(app, "/")

s3 = boto3.resource('s3')
BUCKET = s3.Bucket('alexa-messenger')
BUCKET_NAME = 'alexa-messenger'


@ask.launch
def new_game():
    return question("Welcome to Messenger.")

@ask.intent("AddUserIntent", mapping={'name': 'Recipient'})
def addUser(name):
	# session.attributes['in_progress'] = 'addUser'
	if(name):
		session.attributes['recipient'] = name

	try:
		session.attributes['recipient']
	except:
		return question(render_template('repeat_add_user'))
		
	ID = str(session.user.userId)
	file_name = ID + name + '.txt'
	s3.Object(BUCKET_NAME, file_name ).put(Body=open(file_name, 'w+'))
	return statement('I will add an inbox for you.')

@ask.intent('LeaveMessageIntent', mapping={'sender': 'Sender', 'recipient': 'Recipient', 'message': 'Message'})
def storeMessage(recipient, message):
	key_list = []
	for obj in BUCKET.objects.all():
		key_list.append(obj.key)

	if(recipient):
		session.attributes['recipient'] = recipient
	if(message):
		session.attributes['message'] = message

	try:
		session.attributes['recipient']
	except:
		session.attributes['in_progress'] = "leaveMessageRecipient"
		return question(render_template('repeat_recipient'))

	ID = str(session.user.userId)
	file_name = "{}.txt".format(recipient)
	temp = ID + file_name
	file_name = temp

	obj = s3.Object(BUCKET_NAME,file_name)

	#Check if the recipient has an inbox
	if file_name not in key_list:
		return statement(render_template('need_inbox'))

	try:
		session.attributes['message']
	except:
		return statement(render_template('repeat_message'))
	
	return question(render_template('sender_request'))


@ask.intent("AddSenderIntent", mapping={'name': 'Name'})
def addSender(name):
	session.attributes['sender'] = name

	try:
		session.attributes['sender']
	except:
		session.attributes['in_progress'] = "leaveMessageSender"
		return question(render_template('sender_request'))

	add_sender = session.attributes['sender']
	add_recipient = session.attributes['recipient']
	add_message = session.attributes['message']

	ID = str(session.user.userId)
	file_name = "{}.txt".format(add_recipient)
	temp = ID + file_name
	file_name = temp

	obj = s3.Object(BUCKET_NAME,file_name)
	contents = obj.get()['Body'].read()
	if contents == None:
		# return statement(render_template('empty_inbox'))
		contents = ""
	write_message ='\n ...From ' + add_sender + ': ' + add_message
	contents += write_message
	obj.put(Body=contents)
	return statement(render_template('success_store_message'))


@ask.intent('RetrieveMessageIntent', mapping={'recipient': 'Recipient'})
def retrieveMessage(recipient):
	#retrieve messages for a recipient	
	ID = str(session.user.userId)
	file_name = "{}.txt".format(recipient)
	temp = ID + file_name
	file_name = temp

	#check if the inbox exists
	key_list = []
	for obj in BUCKET.objects.all():
		key_list.append(obj.key)
	if file_name not in key_list:
		return statement(render_template('no_inbox'))

	#return contents and print on card
	obj = s3.Object(BUCKET_NAME,file_name)
	contents = obj.get()['Body'].read()
	return statement(contents).simple_card('Messages', contents)


@ask.intent('DeleteMessageIntent', mapping={'recipient': 'Recipient'})
def clearMessageLog(recipient):
	#clears message log of a particular recipient
	session.attributes['recipient'] = recipient
	try:
		session.attributes['recipient']
	except:
		return question(render_template('repeat_clear_inbox'))

	#create new inbox file
	userID = session.user.userId
	file_name = userID + recipient + '.txt'
	s3.Object(BUCKET_NAME, file_name ).put(Body=open(file_name, 'w+'))
	return statement('success_clear_inbox')

@ask.intent("AMAZON.StopIntent")
def stop():
	response = render_template('stop')
	return statement(response)

@ask.intent("AMAZON.CancelIntent")
def cancel():
	return statement(render_template('stop'))

@ask.intent("AMAZON.HelpIntent")
def help():
	return question(render_template('help')).simple_card('Help', render_template('help'))

@ask.session_ended
def session_ended():
	return "", 200

if __name__ == '__main__':
    app.run(debug=True)