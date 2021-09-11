import sqlite3
import os
from databaseconfig import getQuestion
from flask import Flask, render_template, redirect, url_for
from flask_discord import DiscordOAuth2Session, requires_authorization, Unauthorized
from dotenv import dotenv_values
import requests
import string
import random

app = Flask(__name__)
config = dotenv_values('.env')
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "true"

def generateRandomString():
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(10))


app.config['SECRET_KEY'] = generateRandomString()

app.config["DISCORD_CLIENT_ID"] = config['CLIENT_ID']
app.config["DISCORD_CLIENT_SECRET"] = config['CLIENT_SECRET']
app.config["DISCORD_REDIRECT_URI"] =  config['SERVER_ADDRESS'] + '/successful_login'
app.config["DISCORD_BOT_TOKEN"] = config['TOKEN']

discord = DiscordOAuth2Session(app)

def getDiscordUser(id):
    user = requests.get(f"https://discord.com/api/v8/users/{id}", headers={
        "Authorization": f"Bot {config['TOKEN']}"
    })
    return user.json()

@app.route("/")
def home():
    return "hello there"

@app.route("/login/")
def login():
    return discord.create_session()


@app.route("/successful_login")
def callback():
    discord.callback()
    user = discord.fetch_user()
    apiUser = getDiscordUser(user.id)
    data = {
        'user': apiUser
    }
    return render_template("welcome.html", data=data)


@app.errorhandler(Unauthorized)
def redirect_unauthorized(e):
    return redirect(url_for("login"))


@app.route('/questions/<int:id>')
def singleQuestion(id):
    dbConnection = sqlite3.connect("database.db")
    question = getQuestion(dbConnection, id)
    questionAskedBy = getDiscordUser(question['asked_by'])
    data = {
        'question': question,
        'asked_by': questionAskedBy,
    }
    dbConnection.close()
    return render_template('question.html', data=data)


def runFlaskApp():
    app.run(debug=True, port=config['SERVER_PORT'])

if __name__ == "__main__":
    runFlaskApp()
