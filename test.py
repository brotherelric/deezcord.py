import discord
from discord import Button, LinkButton, SelectMenu, SelectOption, ActionRow
from discord.ext import commands

bot = commands.Bot(" ")

x, y, z =   (
    Button("test", "red", emoji="😁"), 
    LinkButton("https://discord.com"),
    SelectMenu([
        SelectOption("hello"),
        SelectOption("woah", emoji="🤣")
    ])
)

@bot.listen()
async def on_message(message: discord.Message):
    if message.content == "!test":
        msg = await message.channel.send("hmm", components=[x, y, z])

bot.run("ODc0MzU3MTEzODY0OTk4OTIy.YRFyhA.w-lFN6Ae_2btyR5BdQJzH8RhjXU")