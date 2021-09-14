from collections import UserDict
import sqlite3
import datetime
from sqlite3.dbapi2 import Cursor
from typing import Tuple
from discord.message import convert_emoji_reaction
from dotenv import dotenv_values

config = dotenv_values(".env")


def create_connection(db_file):
    connection = None
    try:
        connection = sqlite3.connect(db_file)
        return connection
    except sqlite3.Error as e:
        print(e)


def createServersTable(connection: sqlite3.Connection):
    cur = connection.cursor()
    cur.execute(
        """CREATE TABLE servers ( 
        server_id varchar(255),
        server_bot_prefix varchar(255)
     )"""
    )
    cur.close()


def createQuestionsTable(connection: sqlite3.Connection):
    cur = connection.cursor()
    cur.execute(
        """CREATE TABLE questions (
            id INTEGER NOT NULL PRIMARY KEY,
            question varchar(512),
            server_id varchar(255),
            asked_by varchar(255),
            asked_date datetime
        );
    """
    )
    cur.close()


def createAnswersTable(connection: sqlite3.Connection):
    cur = connection.cursor()
    cur.execute(
        """CREATE TABLE answers (
            id INTEGER NOT NULL PRIMARY KEY,
            answer TEXT,
            answered_by varchar(255),
            votes INTEGER DEFAULT 0,
            answered_date datetime,
            question_id INTEGER
        );
    """
    )
    cur.close()


def createUsersTable(connection: sqlite3.Connection):
    cur = connection.cursor()
    cur.execute(
        """CREATE TABLE users (
        id INTEGER NOT NULL PRIMARY KEY,
        user_id varchar(255),
        avatar varchar(255),
        username varchar(255)
    )
    """
    )
    cur.close()


def createUserAnswerVotesTable(connection: sqlite3.Connection):
    cur = connection.cursor()
    cur.execute(
        """CREATE TABLE user_answer_votes (
        user_id INTEGER NOT NULL,
        answer_id INTEGER NOT NULL
    )
    """
    )
    cur.close()


def getCurrentTime():
    return datetime.datetime.now().strftime(config["DATETIME_FORMAT"])


def nowTimeSeconds():
    now = datetime.datetime.now()
    return now.timestamp()


def addServerRow(connection: sqlite3.Connection, server_id, server_prefix):
    cur = connection.cursor()
    cur.execute("SELECT * FROM servers WHERE server_id=?", (server_id,))
    if cur.fetchone():
        cur.close()
        return
    cur.execute(
        "INSERT INTO servers ( server_id, server_bot_prefix ) VALUES ( ?, ? )",
        (server_id, server_prefix),
    )
    connection.commit()
    cur.close()


def getServerPrefix(connection: sqlite3.Connection, server_id):
    cur = connection.cursor()
    cur.execute("SELECT * FROM servers WHERE server_id=?", (server_id,))
    servers = cur.fetchall()
    cur.close()
    try:
        return servers[0][1]
    except Exception:
        return "."


def updateServerPrefix(connection: sqlite3.Connection, server_id, server_prefix):
    cur = connection.cursor()
    cur.execute(
        """
        UPDATE servers
        SET server_bot_prefix = ?
        WHERE server_id = ?
    """,
        (server_prefix, server_id),
    )
    connection.commit()
    cur.close()


def createQuestion(connection: sqlite3.Connection, question, asked_by, server_id):
    cur = connection.cursor()
    cur.execute(
        """
        INSERT INTO questions ( question, server_id, asked_by, asked_date ) VALUES ( ?, ?, ?, ? );
    """,
        (question, server_id, asked_by, getCurrentTime()),
    )
    connection.commit()
    cur.execute(
        """
        SELECT last_insert_rowid();
    """
    )
    questionId = cur.fetchone()[0]
    cur.close()
    return questionId


def getQuestion(connection: sqlite3.Connection, question_id, server_id, asked_by):
    cur = connection.cursor()
    cur.execute(
        """
        SELECT * FROM questions WHERE id=? AND server_id=? AND asked_by=?;
    """,
        (question_id, server_id, asked_by),
    )
    question = cur.fetchone()
    cur.close()
    return {
        "id": question[0],
        "question": question[1],
        "server_id": question[2],
        "asked_by": question[3],
        "asked_date": datetime.datetime.strptime(
            question[4], config["DATETIME_FORMAT"]
        ),
    }


def createAnswer(connection: sqlite3.Connection, question_id, answer, answered_by):
    cur = connection.cursor()
    nowSeconds = nowTimeSeconds()
    cur.execute(
        "INSERT INTO answers (question_id, answer, answered_by, answered_date ) VALUES (?, ?, ?, ?);",
        (question_id, answer, answered_by, nowSeconds),
    )
    connection.commit()
    cur.execute(
        """
        SELECT last_insert_rowid();
    """
    )
    answerId = cur.fetchone()[0]
    answered_by = getUserWithDiscordId(connection, answered_by)
    cur.close()
    return {
        "id": answerId,
        "answer": answer,
        "answered_by": answered_by,
        "votes": 0,
        "answered_date": nowSeconds,
    }


def searchQuestionsInDatabase(connection: sqlite3.Connection, query, serverId):
    cur = connection.cursor()
    cur.execute(
        "SELECT * FROM questions WHERE server_id = ? AND question LIKE ?",
        (serverId, f"%{query}%"),
    )
    questions = cur.fetchall()
    cur.close()

    def mapQuestions(question):
        return {
            "id": question[0],
            "question": question[1],
            "server_id": question[2],
            "asked_by": question[3],
            "asked_date": datetime.datetime.strptime(
                question[4], config["DATETIME_FORMAT"]
            ),
        }

    return list(map(mapQuestions, questions))


def getAnswersForQuestion(
    connection: sqlite3.Connection, question_id, viewing_user_id, authenticated
):
    cur = connection.cursor()
    cur.execute(
        """
        SELECT * FROM answers WHERE question_id=?;
    """,
        (question_id,),
    )
    answers = cur.fetchall()

    def mapping(answer):
        # Getting the data of the person who answered
        answered_by = getUserWithDiscordId(connection, answer[2])
        userHasVoted = False

        if authenticated:
            cur.execute(
                "SELECT * FROM user_answer_votes WHERE user_id=? AND answer_id=?",
                (viewing_user_id, answer[0]),
            )
            vote = cur.fetchone()
            if vote:
                userHasVoted = True
        return {
            "id": answer[0],
            "answer": answer[1],
            "answered_by": answered_by,
            "votes": answer[3],
            "answered_date": answer[4],
            "user_has_voted": userHasVoted,
        }

    answers = list(map(mapping, answers))
    cur.close()
    return answers


def getUser(connection: sqlite3.Connection, user_id):
    cur = connection.cursor()
    cur.execute(
        """
        SELECT * FROM users WHERE user_id=?
    """,
        (user_id,),
    )
    user = cur.fetchone()
    cur.close()
    if user:
        return {
            "id": user[0],
            "user_id": user[1],
            "avatar": user[2],
            "username": user[3],
        }
    return None


def getUserWithDiscordId(connection: sqlite3.Connection, user_id):
    cur = connection.cursor()
    cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cur.fetchone()
    cur.close()
    if user:
        return {
            "id": user[0],
            "user_id": user[1],
            "avatar": user[2],
            "username": user[3],
        }
    return None


def createUser(connection: sqlite3.Connection, user_id, avatar, username):
    user = getUser(connection, user_id)
    if user:
        return user
    cur = connection.cursor()
    cur.execute(
        "INSERT INTO users ( user_id, avatar, username ) VALUES (?, ?, ?);",
        (user_id, avatar, username),
    )
    connection.commit()
    user = getUser(connection, user_id)
    cur.close()
    return user


def toggleAnswerVote(connection: sqlite3.Connection, answer_id, user_id):
    cur = connection.cursor()
    cur.execute(
        "SELECT * FROM user_answer_votes WHERE answer_id=? AND user_id=?",
        (answer_id, user_id),
    )
    previousVote = cur.fetchone()
    if previousVote:
        cur.execute("UPDATE answers SET votes = votes - 1 WHERE id=?", (answer_id,))
        cur.execute(
            "DELETE FROM user_answer_votes WHERE answer_id=? AND user_id=?",
            (answer_id, user_id),
        )
        cur.execute("SELECT * FROM answers WHERE id=?", (answer_id,))
        answer = cur.fetchone()
        answered_by = getUserWithDiscordId(connection, answer[2])
        answer = {
            "id": answer[0],
            "answer": answer[1],
            "answered_by": answered_by,
            "votes": answer[3],
            "answered_date": answer[4],
            "user_has_voted": False,
        }
        connection.commit()
        cur.close()
        return answer
    cur.execute("UPDATE answers SET votes = votes + 1 WHERE id=?", (answer_id,))
    cur.execute(
        "INSERT into user_answer_votes (answer_id, user_id) VALUES (?, ?)",
        (answer_id, user_id),
    )
    cur.execute("SELECT * FROM answers WHERE id=?", (answer_id,))
    answer = cur.fetchone()
    answered_by = getUserWithDiscordId(connection, answer[2])
    answer = {
        "id": answer[0],
        "answer": answer[1],
        "answered_by": answered_by,
        "votes": answer[3],
        "answered_date": answer[4],
        "user_has_voted": True,
    }
    connection.commit()
    cur.close()
    return answer


def dropAllTables(connection: sqlite3.Connection, tables: list):
    cursor = connection.cursor()
    for table in tables:
        cursor.execute(f"DROP TABLE {table}")
    cursor.close()


if __name__ == "__main__":
    connection = create_connection("database.db")
    dropAllTables(connection, ["servers", "questions", "answers", "users"])
    createServersTable(connection)
    createQuestionsTable(connection)
    createAnswersTable(connection)
    createUsersTable(connection)
    createUserAnswerVotesTable(connection)
    connection.close()
