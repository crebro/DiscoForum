import sqlite3
import os
from databaseconfig import (
    addServerRow,
    createQuestion,
    getServerPrefix,
    searchQuestionsInDatabase,
    toggleAnswerVote,
    createAnswer,
    createUser,
    getAnswersForQuestion,
    getQuestion,
    updateServerPrefix,
)
from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    session,
    request,
    jsonify,
)
from functools import wraps
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


def validateRequestsFromBot(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if (
            "validation" in request.headers
            and request.headers.get("validation") == config["SECRET_KEY"]
        ):
            return function(*args, **kwargs)
        else:
            return redirect(url_for("home"))

    return wrapper


def getDiscordUser(id):
    user = requests.get(
        f"https://discord.com/api/v8/users/{id}",
        headers={"Authorization": f"Bot {config['TOKEN']}"},
    )
    return user.json()


@app.route("/")
def home():
    data = {"add_to_server": config["BOT_TO_SERVER"]}
    return render_template("home.html", data=data)


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


@app.route("/api/questions/<int:id>/answers/<int:viewer_id>")
def getAnswersToQuestion(id, viewer_id):
    dbConnection = sqlite3.connect("database.db")
    answers = getAnswersForQuestion(dbConnection, id, viewer_id, authenticated=True)
    return jsonify(answers)


@app.route("/api/noauth/questions/<int:id>/answers/")
def getAnwersToQuestionNoAuth(id):
    dbConnection = sqlite3.connect("database.db")
    answers = getAnswersForQuestion(dbConnection, id, None, authenticated=False)
    return jsonify(answers)


@app.route("/questions/<int:id>/<int:server_id>/<int:asked_by>")
def singleQuestion(id, server_id, asked_by):
    dbConnection = sqlite3.connect("database.db")
    question = getQuestion(dbConnection, id, server_id, asked_by)
    questionAskedBy = getDiscordUser(question["asked_by"])
    authUser = None
    if "DISCORD_USER_ID" in session:
        authUser = getDiscordUser(session["DISCORD_USER_ID"])

    data = {
        "question": question,
        "asked_by": questionAskedBy,
        "auth_user": authUser,
        "socket_address": config["SOCKET_ADDRESS"],
    }
    dbConnection.close()
    return render_template("question.html", data=data)


@app.route("/questions/<int:id>/answer", methods=["POST"])
def submitAnswerToQuestion(id):
    data = request.get_json()
    if not ("answer" in data) or not ("DISCORD_USER_ID" in session):
        return redirect(url_for("home"))
    answerContent = data["answer"]
    dbConnection = sqlite3.connect("database.db")
    loggedInUser = session["DISCORD_USER_ID"]
    answer = createAnswer(dbConnection, id, answerContent, loggedInUser)
    dbConnection.close()
    return jsonify(answer)


@app.route("/api/answer/togglevote/<int:answer_id>", methods=["POST"])
def toggleVote(answer_id):
    if "DISCORD_USER_ID" not in session:
        return redirect(url_for("home"))
    dbConnection = sqlite3.connect("database.db")
    loggedInUser = session["DISCORD_USER_ID"]
    answer = toggleAnswerVote(dbConnection, answer_id, loggedInUser)
    return jsonify(
        {
            "mesage": "Success",
            "answer": answer,
        }
    )


@app.route("/api/servers/create/<int:server_id>", methods=["POST"])
@validateRequestsFromBot
def addServer(server_id):
    dbConnection = sqlite3.connect("database.db")
    addServerRow(dbConnection, server_id, ".")
    return jsonify({"message": "Success adding server to database"})


@app.route("/api/server/updateprefix/<int:server_id>", methods=["POST"])
@validateRequestsFromBot
def updateServerPrefixFromDatabase(server_id):
    dbConnection = sqlite3.connect("database.db")
    data = request.get_json()
    updateServerPrefix(dbConnection, server_id, data["prefix"])
    return jsonify({"message": "success updating server prefix"})


@app.route("/api/server/<int:server_id>")
@validateRequestsFromBot
def getServerPrefixFromDatabase(server_id):
    dbConnection = sqlite3.connect("database.db")
    prefix = getServerPrefix(dbConnection, server_id=server_id)
    return jsonify({"message": "Success getting the server prefix", "prefix": prefix})


@app.route("/api/questions/search/<string:query>/<int:server_id>")
@validateRequestsFromBot
def searchQuestions(query, server_id):
    dbConncection = sqlite3.connect("database.db")
    questions = searchQuestionsInDatabase(dbConncection, query, serverId=server_id)
    return jsonify(questions)


@app.route("/api/questions/create", methods=["POST"])
@validateRequestsFromBot
def createAQuestion():
    dbConnection = sqlite3.connect("database.db")
    data = request.get_json()
    if (
        ("question" not in data)
        or ("asked_by" not in data)
        or ("server_id" not in data)
    ):
        return redirect(url_for("home"))
    questionId = createQuestion(
        dbConnection,
        question=data["question"],
        asked_by=data["asked_by"],
        server_id=data["server_id"],
    )
    data = {"message": "success", "question_id": questionId}
    return jsonify(data)


@app.route("/recieve_session")
def recieveSession():
    return session


def runFlaskApp():
    app.run(debug=True, port=config["SERVER_PORT"])


if __name__ == "__main__":
    runFlaskApp()
