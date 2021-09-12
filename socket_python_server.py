from flask.helpers import make_response
from flask_socketio import SocketIO
import string
import random
from flask import Flask
from dotenv import dotenv_values
from flask_cors import CORS, cross_origin

config = dotenv_values(".env")


def generateRandomString(n):
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(n))


app = Flask(__name__)
CORS(app)
app.config["SECRET_KEY"] = generateRandomString(10)
socketio = SocketIO(app, cors_allowed_origins="http://localhost:3000")


@app.route("/socket.io")
@cross_origin
def socketIOEndpoint():
    return "success"


@socketio.on("send_message")
def handleMessageSend(
    json,
):
    socketio.emit("recieve_mesage", json)


if __name__ == "__main__":
    socketio.run(app, debug=True, port=config["SOCKET_PORT"])
