from flask import Flask, render_template, request, redirect, session, flash
from mysqlconnection import connectToMySQL
import re
from flask_bcrypt import Bcrypt
# create a regular expression object that we can use to run operations on
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')

app = Flask(__name__)
app.secret_key = "ssssssssssssshhh"
secrecy = Bcrypt(app)

def checkLoggedIn():
    if "userID" not in session:
        return False
    else:
        if not checkIDinDB(session['userID']):
            return False
        return True

def checkIDinDB(userID):
    mysql = connectToMySQL('usersdb')
    query = "SELECT id FROM users WHERE id = %(userID)s;"
    data = {
        'userID'    :   userID
    }
    result = mysql.query_db(query, data)
    if result:
        return True
    else:
        return False

def checkEmailInDB(emailA):
    mysql = connectToMySQL('usersdb')
    query = "SELECT id, email FROM users WHERE email = %(email)s;"
    data = {
        'email' :   emailA
    }
    result = mysql.query_db(query, data)
    # print(result)
    if result:
        return True
    else:
        return False

@app.route('/', methods = ['GET'])
def index():
    if checkLoggedIn():
        print("This damn id is", session['userID'])
        return redirect('/wall')
    
    return render_template("index.html")

@app.route('/processNew', methods = ['POST'])
def processNew():
    # Check first name
    if len(request.form['first_name']) < 1:
        flash("Please enter first name", 'fName')
    elif len(request.form['first_name']) < 2:
        flash("First name should be at least 2 characters", 'fName')
    elif request.form['first_name'].isalpha() == False:
        flash("First name should only contain alphabetical characters", 'fName')

    # Check last name
    if len(request.form['last_name']) < 1:
        flash("Please enter last name", 'lName')
    elif len(request.form['last_name']) < 2:
        flash("Last name should be at least 2 characters", 'lName')
    elif request.form['last_name'].isalpha() == False:
        flash("Last name should only contain alphabetical characters", 'lName')

    # Check email
    if len(request.form['email']) < 1:
        flash("Please enter email address", 'email')
    elif not EMAIL_REGEX.match(request.form['email']):
        flash("Email address entered is invalid", 'email')
    elif checkEmailInDB(request.form['email']):
        flash("Email address entered is already registered, please log in", 'email')

    # Check password
    if len(request.form['password']) < 1:
        flash("Please enter a password", 'password')
        flash("Please enter a password", 'pwconfirm')
    elif len(request.form['password']) < 9:
        flash("Please enter a valid password (too short)", 'password')

    # Check password
    elif len(request.form['pw_confirm']) < 1:
        flash("Please confirm your password", 'pwconfirm')
    elif request.form['password'] != request.form['pw_confirm']:
        flash("Passwords do not match", 'pwconfirm')
        flash("Passwords do not match", 'password')
    
    if '_flashes' in session.keys():
        return redirect('/')
    else:
        pw_hash = secrecy.generate_password_hash(request.form['password'], 12)
        print(pw_hash)
        print(secrecy.check_password_hash(pw_hash, request.form['password']))
        mysql = connectToMySQL('usersdb')
        query = ("INSERT INTO users (first_name, last_name, email, password) "+
        "VALUES (%(f_name)s, %(l_name)s, %(email)s, %(password)s);")
        data = {
            'f_name'    :   request.form['first_name'],
            'l_name'    :   request.form['last_name'],
            'email'     :   request.form['email'],
            'password'  :   pw_hash
        }
        result = mysql.query_db(query, data)
        print(result)
        session['userID'] = result
        print("registered user and logged user in: ", request.form['email'])
        return redirect('/wall')

@app.route('/processLogin', methods = ['POST'])
def processLogin():

    # Check email (entered else exists in database)
    if len(request.form['emailL']) < 1:
        flash("Please enter email address", 'emailL')
    # Check password(entered else matches for the email address entered)
    elif len(request.form['passwordL']) < 1:
        flash("Please enter password", "passwordL")

    if '_flashes' in session.keys():
        return redirect('/')
    
    mysql = connectToMySQL('usersDB')
    query = "SELECT id, email, password FROM users WHERE email = %(email)s;"
    data = {
        'email'    :   request.form['emailL']
    }
    result = mysql.query_db(query,data)

    if not result or len(result) > 1:
        flash("Email address entered was not found, please register", 'emailL')
    elif not secrecy.check_password_hash(result[0]['password'], request.form['passwordL']):
        flash("Password entered was incorrect", 'passwordL')
    
    if '_flashes' in session.keys():
        return redirect('/')
    else:
        session['userID'] = result[0]['id']
        return redirect('/wall')

@app.route('/wall')
def wall():
    if not checkLoggedIn():
        return redirect('/')
    
    # Connect to MySQL database
    mysql = connectToMySQL('usersDB')

    # Run query to get logged in users information
    query = "SELECT id, first_name, last_name, email, password FROM users WHERE id = %(userID)s;"
    data = {
        'userID'    :   session['userID']
    }
    user = mysql.query_db(query, data)

    # Run query to get logged in users messages received
    query = ("SELECT messages.id, messages.content, users.first_name as sender FROM users "+
        "LEFT JOIN messages ON users.id = messages.sender_id WHERE messages.receiver_id = %(userID)s;")
    data = {
        'userID'    :   session['userID']
    }
    messages_received = mysql.query_db(query, data)
    count_r = len(messages_received)
    print(messages_received)

    # Run query to get count of logged in users messages sent
    query = "SELECT COUNT(id) as count FROM messages WHERE sender_id = %(userID)s;"
    data = {
        'userID'    :   session['userID']
    }
    result = mysql.query_db(query, data)
    count_s = result[0]['count']

    # Run query to get a list of all users
    query = "SELECT id, first_name, last_name FROM users;"
    users = mysql.query_db(query)

    return render_template("wall.html", user_info = user[0], users = users, count_r = count_r,
        messages = messages_received, count_s = count_s)

@app.route('/newMessage', methods = ['POST'])
def newMessage():
    # Check length of message greater than 0
    if len(request.form['content']) < 1:
        flash("Message field was left blank")

    if '_flashes' in session.keys():
        return redirect('/wall')
    
    mysql = connectToMySQL('usersdb')
    query = ("INSERT INTO messages (content, sender_id, receiver_id) VALUES "+
        "(%(content)s, %(sender)s, %(receiver)s);")
    data = {
        'content'   :   request.form['content'],
        'sender'    :   session['userID'],
        'receiver'  :   request.form['userID']
    }
    result = mysql.query_db(query, data)
    print(result)

    return redirect('/wall')

@app.route('/deleteMessage', methods = ['POST'])
def deleteMessage():
    mysql = connectToMySQL('usersdb')
    query = ("DELETE FROM messages WHERE id = %(messageID)s;")
    data = {
        'messageID' :   request.form['messageID']
    }
    result = mysql.query_db(query, data)
    print(result)

    return redirect('/wall')

@app.route('/logout')
def logout():
    session.pop('userID')
    return redirect('/')

if __name__ == "__main__":
    app.run(debug=True)