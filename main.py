import discord
import asyncio
import json
from time import sleep
from colorama import init
from colorama import Fore, Style

with open('data.json', 'r') as datafile:
    data = json.loads(datafile.read())

token = data["token"]

init()

global targetChannel

global messageauthor

global checkedValue

global custom

matchmaking = False

class roleBot(discord.Client):

    async def mute(self, member: discord.Member):
        global matchmaking
        matchmaking = True
        role = discord.utils.get(member.guild.roles, name=data["newrole"])
        try:
            await member.edit(roles=[role])
        except:
            matchmaking = False

    async def unmute(self, member: discord.Member):
        global matchmaking
        matchmaking = False
        role = discord.utils.get(member.guild.roles, name=data["newrole"])
        await member.remove_roles(role)

    async def emoji_count(self, text):
        emojicount = 0
        for char in text:
            isascii = lambda s: len(s) == len(s.encode())
            if not isascii(char):
                emojicount += 1
        return emojicount

    async def log(self, info):
        infolist = info.split('\n')
        length = 0
        finalinfo = ""
        for item in infolist:
            if len(item) > length:
                length = len(item)
        for item in infolist:
            emojiCount = await self.emoji_count(item)
            spaceLength = (length - len(item) - emojiCount)
            finalinfo = finalinfo + Fore.BLUE + "│ " + Style.RESET_ALL + item + " " + Fore.BLUE + " " * spaceLength + "│" + Style.RESET_ALL + "\n"
        finalinfo = finalinfo[:-1]
        info = finalinfo
        print(Fore.BLUE + "┌─" + "─" * int(length) + "─┐" + Style.RESET_ALL)
        print(str(info) + Style.RESET_ALL)
        print(Fore.BLUE + "└" + "─" * int(length) + "──┘" + Style.RESET_ALL)
        print()

    async def on_ready(self):
        print()
        await self.log('Logged in as:\n' + self.user.name + '\n' + str(self.user.id))
        game = discord.Game(data["commandprefix"] + "help")
        await client.change_presence(status=discord.Status.online, activity=game)
        global matchmaking
        matchmaking = False
        for server in client.guilds:
            for channel in server.channels:
                if channel.name == data["targetchannels"]["welcome"]:
                    global targetChannel
                    targetChannel = channel
                    await self.log("Found #" + targetChannel.name + "\n" + str(targetChannel.id))
                if channel.name == data["targetchannels"]["complaints"]:
                    global complaintsChannel
                    complaintsChannel = channel
                    await self.log("Found #" + complaintsChannel.name + "\n" + str(complaintsChannel.id))

    async def clean_list(self, finput, newlines=False):
        output = ""
        if not newlines:
            i = 0
            while i != len(finput):
                if i == len(finput) - 2:
                    output += finput[i] + ", and "
                else:
                    output += finput[i] + ", "
                i += 1
            return output[:-2]
        else:
            for item in finput:
                output += item + "\n"
            return output[:-1]

    async def helpmessage(self, message):
        em = discord.Embed(title="**All Commands**", description="\n*Prefix is " + data["commandprefix"] + "*\n**" + data["commandprefix"] + "matchmake**\nRestarts the inital matchmaking process\n**" + data["commandprefix"] + "complain <message>**\nSends a private messaage to moderators\n**" + data["commandprefix"] + "roleassign**\nReassigns custom moderator given roles (won't always work depending on the server)\n**" + data["commandprefix"] + "help**\nDisplays this help message")
        await message.channel.send(embed=em)

    async def on_message(self, message):
        global matchmaking
        dm = False
        try:
            msglist = ["From: " + str(message.author), "Sent in: " + str(message.author.guild) + " in #" + str(message.channel), "Content: " + str(message.content)]
        except AttributeError:
            msglist = ["From: " + str(message.author), "In a " + str(message.channel), "Content: " + str(message.content)]
            dm = True
        finalmsg = ""
        for msg in msglist:
            finalmsg = finalmsg + msg + '\n'
        finalmsg = finalmsg[:-1]
        await self.log(finalmsg)
        if dm:
            return
        if "new member" not in [role.name.lower() for role in message.author.roles]:
            if message.content == data["commandprefix"] + "matchmake":
                await message.delete()
                if not matchmaking:
                    statusmsg = await message.channel.send(content="Matchmaking " + message.author.mention + "...")
                    await self.matchmake(message.author)
                    await statusmsg.delete()
                else:
                    em = discord.Embed(title="ERROR", description="\nAlready matchmaking someone else, please try again soon!")
                    statusmsg = await message.channel.send(embed=em)
                    sleep(2)
                    await statusmsg.delete()
            elif message.content == data["commandprefix"] + "roleassign":
                await message.delete()
                await self.roleassign(message=message)
            elif message.content == data["commandprefix"] + "help":
                await self.helpmessage(message)
            else:
                msglist = message.content.split()
                if len(msglist) > 0 and msglist[0] == data["commandprefix"] + "complain":
                    await self.complain(message)
        else:
            await message.delete()

    async def complain(self, message):
        complaint = message.content.replace(data["commandprefix"] + "complain ", "")
        await message.delete()
        em = discord.Embed(title="Success", description="\nComplaint has been sent to moderators!")
        msg = await message.channel.send(embed=em)
        em = discord.Embed(title="Complaint Recieved", description="\n" + str(complaint))
        await complaintsChannel.send(embed=em)
        sleep(2)
        await msg.delete()

    async def roleassign(self, member=None, message=None):
        if message is not None:
            member = message.author
        membername = str(member)
        if membername in data["assignedroles"].keys():
            for role in data["assignedroles"][membername]:
                role = discord.utils.get(member.guild.roles, name=role)
                await member.add_roles(role)
            if message is not None:
                rolelist = data["assignedroles"][membername]
                rolelist = await self.clean_list(rolelist)
                em = discord.Embed(title="Success", description="\nAssigned the following roles: " + rolelist + ".")
                msg = await message.channel.send(embed=em)
                sleep(2)
                await msg.delete()
        else:
            if message is not None:
                await message.channel.send("Failed to assign roles, please contact " + "<@" + data["admintoken"] + "> to fix this.")

    def emojicheck(self, reaction, user):
        global messageauthor
        global checkedValue
        global custom
        if not custom:
            return messageauthor == user and str(reaction.emoji) in checkedValue
        else:
            for item in checkedValue:
                if str(reaction.emoji) == str(item):
                    return messageauthor == user
            return False

    def textcheck(self, message):
        global messageauthor
        global targetChannel
        return messageauthor == message.author and str(message.channel) == str(targetChannel)

    async def matchmake(self, member):
        await self.log("Matchmaking:\n" + str(member))
        global matchmaking
        global messageauthor
        global checkedValue
        global custom
        if matchmaking:
            em = discord.Embed(title="ERROR", description="\nAlready matchmaking someone else, please try again soon!")
            try:
                await member.send(embed=em)
                await member.send(data["serverinvite"])
            except discord.errors.Forbidden:
                pass
            await member.kick()
            return
        if not member.bot:
            totalquestions = len(data["questions"].keys())
            await self.mute(member)
            if not matchmaking:
                return
            welcomemsg = await targetChannel.send(content=member.mention + ", welcome to " + data["servername"] + ". In order to begin, please answer the following questions.")
            i = 1
            for name in data["questions"]:
                custom = False
                additions = ""
                if data["questions"][name]["reactiontype"] == "text":
                    optionlist = data["questions"][name]["answers"]
                    optionlist = await self.clean_list(optionlist, newlines=True)
                    additions = "\n\nPlease reply to the message with one of these options:\n" + optionlist
                em = discord.Embed(title="Question " + str(i) + "/" + str(totalquestions) + ":", description="\n" + data["questions"][name]["question"] + additions)
                msg = await targetChannel.send(embed=em)
                if data["questions"][name]["reactiontype"] == "text":
                    while True:
                        await self.log("Getting user input...")
                        role = discord.utils.get(member.guild.roles, name=data["textrole"])
                        await member.add_roles(role)
                        messageauthor = member
                        try:
                            usermsg = await client.wait_for('message', check=self.textcheck, timeout=120)
                        except asyncio.TimeoutError:
                            usermsg = None
                        await self.log("Recieved message: " + str(usermsg.content))
                        if usermsg is None:
                            await self.log("Timed out")
                            matchmaking = False
                            await welcomemsg.delete()
                            try:
                                await member.send("Timed out, rejoin " + data["servername"] + " to try again.")
                                await member.send(data["serverinvite"])
                            except discord.errors.Forbidden:
                                pass
                            await member.kick()
                            break
                        try:
                            await usermsg.delete()
                        except discord.errors.NotFound:
                            pass
                        msgcontent = usermsg.content
                        loweranswers = []
                        for item in data["questions"][name]["answers"]:
                            loweranswers.append(item.lower())
                        if msgcontent.lower() in loweranswers:
                            role = discord.utils.get(member.guild.roles, name=data["textrole"])
                            await member.remove_roles(role)
                            if data["questions"][name]["roles"] == 0:
                                answerIndex = loweranswers.index(msgcontent.lower())
                                role = discord.utils.get(member.guild.roles, name=data["questions"][name]["answers"][answerIndex])
                                await member.add_roles(role)
                                break
                            else:
                                answerIndex = loweranswers.index(msgcontent)
                                role = discord.utils.get(member.guild.roles, name=data["questions"][name]["roles"][answerIndex])
                                await member.add_roles(role)
                                break
                    await msg.delete()
                    if usermsg is None:
                        msg = usermsg
                        break
                    i += 1
                    continue
                while True:
                    if data["questions"][name]["reactiontype"] == "custom":
                        custom = True
                        emojis = []
                        for emoji in data["questions"][name]["answers"]:
                            emojis.append(discord.utils.get(client.emojis, name=emoji))
                    else:
                        emojis = data["questions"][name]["answers"]
                    await self.log("Possibile Responses are:\n" + str(emojis))
                    for emoji in emojis:
                        await msg.add_reaction(emoji)
                    messageauthor = member
                    checkedValue = emojis
                    try:
                        res = await client.wait_for('reaction_add', check=self.emojicheck, timeout=120)
                    except asyncio.TimeoutError:
                        res = None
                    if res is None:
                        await self.log("Timed out")
                        matchmaking = False
                        await msg.delete()
                        await welcomemsg.delete()
                        try:
                            await member.send("Timed out, rejoin " + data["servername"] + " to try again.")
                            await member.send(data["serverinvite"])
                        except discord.errors.Forbidden:
                            pass
                        await member.kick()
                        break
                    res = res[0]
                    if data["questions"][name]["reactiontype"] == "custom":
                        res = res.emoji.name
                        res = res.lower()
                    else:
                        res = res.emoji
                    if res in data["questions"][name]["answers"]:
                        answerIndex = data["questions"][name]["answers"].index(res)
                        await self.log("Emoji at index:\n" + str(answerIndex))
                        break
                if res is None:
                    msg = res
                    break
                else:
                    if data["questions"][name]["type"] == "role" and data["questions"][name]["roles"][answerIndex] != "":
                        role = discord.utils.get(member.guild.roles, name=data["questions"][name]["roles"][answerIndex])
                        await self.log("Assigning role:\n" + str(role))
                        await member.add_roles(role)
                    if data["questions"][name]["type"] == "action":
                        if data["questions"][name]["actions"][answerIndex] == "close":
                            await msg.delete()
                            break
                await msg.delete()
                i += 1
            if msg is not None:
                await self.unmute(member)
                await targetChannel.send("Welcome to " + data["servername"] + ", " + member.mention + ".")
                await welcomemsg.delete()
                await self.roleassign(member=member)

    async def on_member_join(self, member):
        await self.matchmake(member)

client = roleBot()
client.run(token)