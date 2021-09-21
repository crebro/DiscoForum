from discord_components import DiscordComponents, Button, ButtonStyle, Interaction
from dotenv import dotenv_values
import discord
import datetime
import requests

config = dotenv_values(".env")
requestsConfigurationHeaders = {"validation": config["SECRET_KEY"]}


def addServerRow(server_id):
    requests.post(
        f"{config['SERVER_ADDRESS']}/api/servers/create/{server_id}",
        headers=requestsConfigurationHeaders,
    )


def createQuestion(question, asked_by, server_id):
    data = {"question": question, "asked_by": asked_by, "server_id": server_id}
    response = requests.post(
        f"{config['SERVER_ADDRESS']}/api/questions/create",
        json=data,
        headers=requestsConfigurationHeaders,
    ).json()
    return response["question_id"]


def getServerPrefix(server_id):
    response = requests.get(
        f"{config['SERVER_ADDRESS']}/api/server/{server_id}",
        headers=requestsConfigurationHeaders,
    ).json()
    return response["prefix"]


def searchQuestionsInDatabase(query, server_id):
    response = requests.get(
        f"{config['SERVER_ADDRESS']}/api/questions/search/{query}/{server_id}",
        headers=requestsConfigurationHeaders,
    ).json()
    return response


def updateServerPrefix(sever_id, prefix):
    data = {
        "prefix": prefix,
    }
    response = requests.post(
        f"{config['SERVER_ADDRESS']}/api/server/updateprefix/{sever_id}",
        json=data,
        headers=requestsConfigurationHeaders,
    ).json()
    return response


class BotClient(discord.Client):
    def __init__(self, **options):
        super().__init__(**options)

    async def on_ready(self):
        print("Logged in as", self.user)
        DiscordComponents(
            self,
        )

    async def on_guild_join(self, guild: discord.Guild):
        addServerRow(guild.id)

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
                    updateServerPrefix(serverId, splitMessage[1])
                    await message.reply(
                        f"Successfully Updated Server Prefix to {splitMessage[1]}"
                    )
                except Exception as e:
                    await message.reply("Please send a valid command")
            elif self.checkCommandString(messageContent, serverPrefix, "ask"):
                await self.registerQuestion(message, serverId)
            elif self.checkCommandString(messageContent, serverPrefix, "search"):
                await self.serachForQuestions(message, serverId)
        else:
            await message.reply("I didn't get that message at all")

    def getPrefix(self, server_id):
        return getServerPrefix(server_id=server_id)

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
            questionID = createQuestion(question, message.author.id, serverId)
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
            await message.channel.send("Please send a valid command")
            await message.delete()

    async def serachForQuestions(self, message: discord.Message, serverId):
        messageContent = message.content
        splitMessage = messageContent.split(" ", 1)
        query = splitMessage[1]
        questions = searchQuestionsInDatabase(query, serverId)
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


client = BotClient()
client.run(config["TOKEN"])
