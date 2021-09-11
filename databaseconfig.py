import sqlite3
import datetime
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
            answer varchar(512),
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
        login_token varchar(255) 
    )
    """
    )
    cur.close()


def getCurrentTime():
    return datetime.datetime.now().strftime(config["DATETIME_FORMAT"])


def addServerRow(connection: sqlite3.Connection, server_id, server_prefix):
    cur = connection.cursor()
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


def getQuestion(connection: sqlite3.Connection, question_id):
    cur = connection.cursor()
    cur.execute(
        """
        SELECT * FROM questions WHERE id=?;
    """,
        (question_id,),
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
    cur.execute(
        "INSERT INTO answers (question_id, answer, answered_by, answered_date ) VALUES (?, ?, ?, ?);",
        (question_id, answer, answered_by, getCurrentTime()),
    )
    connection.commit()


def getAnswersForQuestion(connection: sqlite3.Connection, question_id):
    cur = connection.cursor()
    cur.execute(
        """
        SELECT * FROM answers WHERE question_id=?;
    """,
        (question_id,),
    )
    answers = cur.fetchall()
    cur.close()

    def mapping(answer):
        return {
            "id": answer[0],
            "answer": answer[1],
            "answered_by": answer[2],
            "votes": answer[3],
            "answered_date": answer[4],
        }

    return list(map(mapping, answers))


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
    return {
        "id": user[0],
        "name": user[1],
        "token": user[2],
    }


def getUserWithToken(connection: sqlite3.Connection, token):
    cur = connection.cursor()
    cur.execute("SELECT * FROM users WHERE login_token=?", (token))
    user = cur.fetchone()
    cur.close()
    return user


def createUser(connection: sqlite3.Connection, user_id, token):
    user = getUser(connection, user_id)
    print(user)
    if user:
        return user
    cur = connection.cursor()
    cur.execute(
        "INSERT INTO users ( user_id, login_token ) VALUES (?, ?);", (user_id, token)
    )
    connection.commit()
    cur.execute("SELECT last_insert_rowid();")
    userId = cur.fetchone()[0]
    user = getUser(connection, userId)
    cur.close()
    return user


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
    connection.close()
