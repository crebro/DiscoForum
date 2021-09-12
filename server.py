import sqlite3
import os
from databaseconfig import createAnswer, createUser, getAnswersForQuestion, getQuestion
from flask import Flask, render_template, redirect, url_for, session, request, jsonify
from flask_discord import DiscordOAuth2Session, requires_authorization, Unauthorized
from dotenv import dotenv_values
import requests
import string
import random

app = Flask(__name__)
config = dotenv_values(".env")
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "true"


def generateRandomString(n):
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(n))


app.config["SECRET_KEY"] = generateRandomString(10)

app.config["DISCORD_CLIENT_ID"] = config["CLIENT_ID"]
app.config["DISCORD_CLIENT_SECRET"] = config["CLIENT_SECRET"]
app.config["DISCORD_REDIRECT_URI"] = config["SERVER_ADDRESS"] + "/successful_login"
app.config["DISCORD_BOT_TOKEN"] = config["TOKEN"]

discord = DiscordOAuth2Session(app)


def getDiscordUser(id):
    user = requests.get(
        f"https://discord.com/api/v8/users/{id}",
        headers={"Authorization": f"Bot {config['TOKEN']}"},
    )
    return user.json()


@app.route("/")
def home():
    return "hello there"


@app.route("/login/")
def login():
    return discord.create_session()


@app.route("/successful_login")
def callback():
    dbConnection = sqlite3.connect("database.db")
    discord.callback()
    user = discord.fetch_user()
    apiUser = getDiscordUser(user.id)
    createUser(dbConnection, user.id, apiUser["avatar"], apiUser["username"])
    dbConnection.close()
    data = {"user": apiUser}
    return render_template("welcome.html", data=data)


@app.errorhandler(Unauthorized)
def redirect_unauthorized(e):
    return redirect(url_for("login"))


@app.route("/api/questions/<int:id>/answers")
def getAnswersToQuestion(id):
    dbConnection = sqlite3.connect("database.db")
    answers = getAnswersForQuestion(dbConnection, id)
    return jsonify(answers)


@app.route("/questions/<int:id>")
def singleQuestion(id):
    dbConnection = sqlite3.connect("database.db")
    question = getQuestion(dbConnection, id)
    questionAskedBy = getDiscordUser(question["asked_by"])
    authUser = None
    # answers = getAnswersForQuestion(dbConnection, question["id"])
    if "DISCORD_USER_ID" in session:
        authUser = getDiscordUser(session["DISCORD_USER_ID"])

    data = {
        "question": question,
        "asked_by": questionAskedBy,
        "auth_user": authUser,
        "socket_address": config["SOCKET_ADDRESS"]
        # "answers": answers,
    }
    dbConnection.close()
    return render_template("question.html", data=data)


@app.route("/questions/<int:id>/answer", methods=["POST"])
def submitAnswerToQuestion(id):
    data = request.get_json()
    if not ("answer" in data) or not ("DISCORD_USER_ID" in session):
        return redirect(url_for("singleQuestion", id=id))
    answerContent = data["answer"]
    dbConnection = sqlite3.connect("database.db")
    loggedInUser = session["DISCORD_USER_ID"]
    answer = createAnswer(dbConnection, id, answerContent, loggedInUser)
    dbConnection.close()
    return jsonify(answer)


@app.route("/recieve_session")
def recieveSession():
    return session


def runFlaskApp():
    app.run(debug=True, port=config["SERVER_PORT"])


if __name__ == "__main__":
    runFlaskApp()
