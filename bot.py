from discord import message
from discord_components import DiscordComponents, Button, ButtonStyle, Interaction
from databaseconfig import (
    addServerRow,
    create_connection,
    createQuestion,
    getServerPrefix,
    searchQuestionsInDatabase,
    updateServerPrefix,
)
from dotenv import dotenv_values
import discord
import datetime

config = dotenv_values(".env")


class BotClient(discord.Client):
    def __init__(self, connection, **options):
        self.dbconnection = connection
        super().__init__(**options)

    async def on_ready(self):
        print("Logged in as", self.user)
        DiscordComponents(
            self,
        )

    async def on_guild_join(self, guild: discord.Guild):
        addServerRow(self.dbconnection, guild.id, ".")

    async def on_message(self, message: discord.Message):
        if message.author == self.user:
            return

        messageContent = message.content
        serverId = message.guild.id
        serverPrefix = self.getPrefix(serverId)
        if messageContent.startswith(serverPrefix):
            if self.checkCommandString(messageContent, serverPrefix, "changePrefix"):
                splitMessage = messageContent.split(" ", 1)
                try:
                    updateServerPrefix(self.dbconnection, serverId, splitMessage[1])
                except Exception:
                    await message.reply("Please send a valid command")
            elif self.checkCommandString(messageContent, serverPrefix, "ask"):
                await self.registerQuestion(message, serverId)
            elif self.checkCommandString(messageContent, serverPrefix, "search"):
                await self.serachForQuestions(message, serverId)
        else:
            await message.reply("I didn't get that message at all")

    def getPrefix(self, server_id):
        return getServerPrefix(self.dbconnection, server_id=server_id)

    def checkCommandString(self, message, prefix, command):
        return message.startswith(f"{prefix}{command}")

    def getRouteForQuestion(self, question_id, server_id, asked_by):
        return (
            config["SERVER_ADDRESS"]
            + f"/questions/{question_id}/{server_id}/{asked_by}"
        )

    async def registerQuestion(self, message: discord.Message, serverId):
        messageContent = message.content
        splitMessage = messageContent.split(" ", 1)
        question = splitMessage[1]
        try:
            questionID = createQuestion(
                self.dbconnection, question, message.author.id, serverId
            )
            now = datetime.datetime.now()
            questionEmbed = discord.Embed(
                title=f"Question by {message.author.display_name}",
                description=f"Question: {question}",
            )
            questionEmbed.set_footer(
                text=f"Asked Date: {now.year}-{now.month}-{now.day}"
            )
            questionEmbed.set_thumbnail(url=message.author.avatar_url)
            await message.channel.send(
                embed=questionEmbed,
                components=[
                    Button(
                        style=ButtonStyle.URL,
                        label="Answer This Question",
                        url=self.getRouteForQuestion(
                            questionID, serverId, message.author.id
                        ),
                    )
                ],
            )
            await message.delete()
        except Exception as e:
            print(e)
            await message.channel.send("Please send a valid command")
            await message.delete()

    async def serachForQuestions(self, message: discord.Message, serverId):
        messageContent = message.content
        splitMessage = messageContent.split(" ", 1)
        query = splitMessage[1]
        questions = searchQuestionsInDatabase(self.dbconnection, query, serverId)
        questionsEmbed = discord.Embed(
            title=f"Search results for '{query}'",
            description=f"Your Query Returned { len(questions) if len(questions) != 0 else 'no' } results",
            color=discord.Color.from_rgb(9, 127, 237),
        )
        for question in questions:
            questionThreadUrl = self.getRouteForQuestion(
                question["id"], serverId, question["asked_by"]
            )
            questionsEmbed.add_field(
                name=question["question"],
                value=f"[View Question Thread]({questionThreadUrl})",
            )
        await message.channel.send(embed=questionsEmbed)


connection = create_connection("database.db")
client = BotClient(connection)
client.run(config["TOKEN"])
connection.close()
