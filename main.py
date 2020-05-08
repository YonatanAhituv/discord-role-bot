import discord
import asyncio
import json
from time import sleep
from colorama import init
from colorama import Fore, Style

with open('config.json', 'r') as configfile:
    config = json.loads(configfile.read())

redis = False
if config["assignedroles"]["db"] or config["bio"]["enabled"] or config["mee6"]["enabled"]:
    redis = True
    import db

if config["mee6"]["enabled"]:
    import requests

token = config["token"]

init()

global targetChannel

global r

global messageauthor

global server

global checkedValue

global custom

matchmaking = False


class roleBot(discord.Client):

    def getLeaderboard(self):
        global server
        baseurl = "http://mee6.xyz/api/plugins/levels/leaderboard/"
        response = requests.get(baseurl + str(server.id))
        response = json.loads(response.text)
        finaldict = {}
        for item in response["players"]:
            finaldict[item["id"]] = item["level"]
        return finaldict

    async def assignLevels(self):
        await self.log("Checking MEE6 levels...")
        levels = self.getLeaderboard()
        for item in list(levels.keys()):
            if levels[item] < config["mee6"]["level"]:
                levels.pop(item)
                continue
            user = db.getMember(item)
            if "roles" not in user.keys():
                user["roles"] = []
            else:
                user["roles"] = db.stringListToList(user["roles"])
            if config["mee6"]["levelrole"] in user["roles"]:
                levels.pop(item)
                continue
            user["roles"].append(config["mee6"]["levelrole"])
            user["roles"] = str(user["roles"])
            r.hmset(item, user)
            member = discord.utils.get(server.members, id=int(item))
            if member is None:
                continue
            await self.roleassign(member=member)
        await self.log("Checked MEE6 Levels")

    async def mute(self, member: discord.Member):
        global matchmaking
        matchmaking = True
        role = discord.utils.get(member.guild.roles, name=config["matchmaking"]["newrole"])
        if role is None:
            await self.log("WARNING:\nCould not find New Member role, make sure \"newrole\" is set in config.json")
            return
        try:
            await member.edit(roles=[role])
        except discord.errors.NotFound:
            matchmaking = False
        except discord.errors.Forbidden:
            await self.log("ERROR:\nNot enough permissions to matchmake, make sure the bot's role is at the top")
            matchmaking = False

    async def unmute(self, member: discord.Member):
        global matchmaking
        matchmaking = False
        role = discord.utils.get(member.guild.roles, name=config["matchmaking"]["newrole"])
        if role is None:
            return
        await member.remove_roles(role)

    async def emoji_count(self, text):
        emojicount = 0
        for char in text:
            if len(char) != len(char.encode()):
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
        print()
        print(Fore.BLUE + "┌─" + "─" * int(length) + "─┐" + Style.RESET_ALL)
        print(str(info) + Style.RESET_ALL)
        print(Fore.BLUE + "└" + "─" * int(length) + "──┘" + Style.RESET_ALL)

    async def on_ready(self):
        print()
        await self.log('Logged in as:\n' + self.user.name + '\n' + str(self.user.id))
        # game = discord.Game(config["botpresence"].replace("{help}", config["commandprefix"] + "help"))
        activity = discord.Activity(name=config["presence"]["message"].replace("{help}", config["commandprefix"] + "help"), type=config["presence"]["type"])
        await client.change_presence(status=discord.Status.online, activity=activity)
        if redis:
            global r
            r = db.redisInit()
            await self.log("Database imported with " + str(len(r.keys())) + " keys")
        global matchmaking
        global server
        matchmaking = False
        for server in client.guilds:
            for channel in server.channels:
                if config["matchmaking"]["enabled"]:
                    if channel.name == config["matchmaking"]["welcomechannel"]:
                        global targetChannel
                        targetChannel = channel
                        await self.log("Found #" + targetChannel.name + "\n" + str(targetChannel.id))
                if config["complaints"]["enabled"]:
                    if channel.name == config["complaints"]["complaintschannel"]:
                        global complaintsChannel
                        complaintsChannel = channel
                        await self.log("Found #" + complaintsChannel.name + "\n" + str(complaintsChannel.id))
        if config["mee6"]["enabled"]:
            await self.assignLevels()

    async def clean_list(self, finput, newlines=False, numbers=False):
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
            i = 1
            for item in finput:
                if numbers:
                    output += str(i) + ". " + item + "\n"
                if not numbers:
                    output += item + "\n"
                i += 1
            return output[:-1]

    async def helpmessage(self, message):
        commands = {
            "matchmaking": "**{}matchmake**\nRestarts the inital matchmaking process",
            "complaints": "**{}complain <message>**\nSends a private message to moderators",
            "bio": "**{}bio set <message>**\nSets a bio message for your user\n**{}bio show <user mention>**\nReturns the mentioned user's bio",
            "assignedroles": "**{}roleassign**\nReassigns custom moderator given roles (won't always work depending on the server)"
        }
        info = "*Prefix is {}*"
        helpmessage = ""
        helpmessage += info + "\n"
        for item in commands:
            if config[item]["enabled"]:
                helpmessage += commands[item] + "\n"
        helpmessage += "**{}help**\nDisplays this help message"
        helpmessage = helpmessage.replace("{}", config["commandprefix"])
        em = discord.Embed(title="**All Commands**", description=helpmessage)
        await message.channel.send(embed=em)

    async def on_message(self, message):
        if message.author.id == self.user.id:
            return
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
        if str(message.author.id) == "159985870458322944" and config["mee6"]["enabled"] and message.channel.name == config["mee6"]["levelchannel"]:
            await self.assignLevels()
        if "new member" not in [role.name.lower() for role in message.author.roles]:
            if config["matchmaking"]["enabled"] and message.content == config["commandprefix"] + "matchmake":
                await message.delete()
                if not matchmaking:
                    em = discord.Embed(title="STATUS", description="\nMatchmaking " + message.author.mention + "...")
                    statusmsg = await message.channel.send(embed=em)
                    try:
                        await self.matchmake(message.author)
                    except (KeyError, discord.errors.HTTPException, AttributeError) as e:
                        await self.log("ERROR\n" + str(e))
                        await self.cancelmatchmake("\nSomething went wrong. Try again later.")
                    await statusmsg.delete()
                else:
                    em = discord.Embed(title="ERROR", description="\nAlready matchmaking someone else, please try again soon!")
                    statusmsg = await message.channel.send(embed=em)
                    sleep(2)
                    await statusmsg.delete()
            elif config["assignedroles"]["enabled"] and message.content == config["commandprefix"] + "roleassign":
                await message.delete()
                await self.roleassign(message=message)
            elif message.content == config["commandprefix"] + "help":
                await self.helpmessage(message)
            else:
                msglist = message.content.split()
                if config["complaints"]["enabled"] and len(msglist) > 0 and msglist[0] == config["commandprefix"] + "complain":
                    await self.complain(message)
                elif config["bio"]["enabled"] and len(msglist) >= 3 and msglist[0] == config["commandprefix"] + "bio":
                    await self.bio(message, msglist)
        else:
            await message.delete()

    async def on_raw_reaction_add(self, payload):
        if not config["reactionlimits"]["enabled"]:
            return
        targetpoll = {}
        for poll in config["reactionlimits"]["polls"]:
            if str(payload.message_id) == config["reactionlimits"]["polls"][poll]["messageid"] and str(payload.channel_id) == config["reactionlimits"]["polls"][poll]["reactionchannel"]:
                targetpoll = config["reactionlimits"]["polls"][poll]
        for server in client.guilds:
            for channel in server.channels:
                if str(channel.id) == targetpoll["reactionchannel"]:
                    global reactionChannel
                    reactionChannel = channel
        reactionMessage = await reactionChannel.fetch_message(targetpoll["messageid"])
        if payload.message_id == reactionMessage.id:
            i = 0
            userIDList = []
            for reaction in reactionMessage.reactions:
                users = await reaction.users().flatten()
                for user in users:
                    userIDList.append(user.id)
            for userID in userIDList:
                if payload.user_id == userID:
                    i += 1
            member = discord.utils.get(server.members, id=int(payload.user_id))
            memberRoles = []
            for role in member.roles:
                memberRoles.append(role.name)
            if i > targetpoll["limit"] or any(elem in targetpoll["bannedroles"] for elem in memberRoles):
                for reaction in reactionMessage.reactions:
                    await reaction.remove(member)

    async def complain(self, message):
        if config["complaints"]["anonymized"]:
            title = "**Complaint Recieved**"
        else:
            title = "**Complaint Recieved From: ** " + message.author.display_name
        complaint = message.content.replace(config["commandprefix"] + "complain ", "")
        await message.delete()
        em = discord.Embed(title="SUCCESS", description="\nComplaint has been sent to moderators!")
        msg = await message.channel.send(embed=em)
        em = discord.Embed(title=title, description="\n" + str(complaint))
        await complaintsChannel.send(embed=em)
        sleep(2)
        await msg.delete()

    async def bio(self, message, msglist):
        global r
        if msglist[1] == "set" and len(msglist) >= 3:
            memberid = str(message.author.id)
            bio = message.content.replace(config["commandprefix"] + "bio set ", "")
            await message.delete()
            user = db.getMember(memberid)
            user["bio"] = bio
            r.hmset(memberid, user)
            await self.log("Added new bio, key is: " + str(memberid) + " and bio is: " + str(bio))
            em = discord.Embed(title="SUCCESS", description="\nBio has been saved to database!")
            msg = await message.channel.send(embed=em)
            sleep(2)
            await msg.delete()
        if msglist[1] == "show" and len(msglist) == 3:
            userid = msglist[2].replace("<@", "").replace("!", "").replace(">", "")
            await self.log("Getting " + str(userid) + "'s bio...")
            try:
                bio = db.getMember(userid)
                bio = bio["bio"]
            except (AttributeError, KeyError):
                await message.delete()
                em = discord.Embed(title="ERROR", description="\n" + "Specified member does not have a bio.")
                msg = await message.channel.send(embed=em)
                sleep(2)
                await msg.delete()
                return
            user = discord.utils.get(client.get_all_members(), id=int(userid))
            em = discord.Embed(title=user.display_name + "'s Bio", description="\n" + str(bio))
            await message.channel.send(embed=em)

    async def roleassign(self, member=None, message=None):
        if config["assignedroles"]["db"]:
            await self.dbRoleAssign(member=member, message=message)
        else:
            await self.jsonRoleAssign(member=member, message=message)

    async def jsonRoleAssign(self, member=None, message=None):
        if message is not None:
            member = message.author
        membername = str(member)
        memberid = str(member.id)
        memberNameKeys = membername in config["assignedroles"].keys()
        memberIdKeys = memberid in config["assignedroles"].keys()
        everyoneKeys = "everyone" in config["assignedroles"].keys()
        if memberNameKeys or memberIdKeys or everyoneKeys:
            if memberNameKeys:
                membervalue = membername
            elif memberIdKeys:
                membervalue = memberid
            else:
                membervalue = None
            if membervalue in config["assignedroles"].keys():
                givenroles = config["assignedroles"][membervalue].copy()
            else:
                givenroles = []
            if "everyone" in config["assignedroles"].keys():
                for role in config["assignedroles"]["everyone"]:
                    givenroles.append(role)
            rolelist = await self.clean_list(givenroles)
            roles = []
            for role in givenroles:
                role = discord.utils.get(member.guild.roles, name=role)
                if role is None:
                    em = discord.Embed(title="ERROR", description="\nFailed to assign the following roles: " + rolelist + ".")
                    msg = await message.channel.send(embed=em)
                    sleep(2)
                    await msg.delete()
                    message = None
                    break
                roles.append(role)
            for role in roles:
                await member.add_roles(role)
            if message is not None:
                em = discord.Embed(title="SUCCESS", description="\nAssigned the following roles: " + rolelist + ".")
                msg = await message.channel.send(embed=em)
                sleep(2)
                await msg.delete()
        else:
            if message is not None:
                em = discord.Embed(title="ERROR", description="\nFailed to assign roles, if you think this is an error, please contact " + "<@" + config["admintoken"] + "> to fix this.")
                msg = await message.channel.send(embed=em)
                sleep(2)
                await msg.delete()

    async def dbRoleAssign(self, member=None, message=None):
        if message is not None:
            member = message.author
        user = db.getMember(str(member.id))
        isMember = "roles" in user.keys()
        isEveryone = "everyone" in db.redisKeys()
        if isMember or isEveryone:
            givenroles = []
            if isMember:
                roles = db.stringListToList(user["roles"])
                for role in roles:
                    givenroles.append(role)
            if isEveryone:
                everyone = db.getList("everyone")
                for role in everyone:
                    givenroles.append(role)
            rolelist = await self.clean_list(givenroles)
            roles = []
            for role in givenroles:
                role = discord.utils.get(member.guild.roles, name=role)
                if role is None:
                    if message is not None:
                        em = discord.Embed(title="ERROR", description="\nFailed to assign the following roles: " + rolelist + ".")
                        msg = await message.channel.send(embed=em)
                        sleep(2)
                        await msg.delete()
                        message = None
                    break
                roles.append(role)
            for role in roles:
                await member.add_roles(role)
            if message is not None:
                em = discord.Embed(title="SUCCESS", description="\nAssigned the following roles: " + rolelist + ".")
                msg = await message.channel.send(embed=em)
                sleep(2)
                await msg.delete()
        else:
            if message is not None:
                em = discord.Embed(title="ERROR", description="\nFailed to assign roles, if you think this is an error, please contact " + "<@" + config["admintoken"] + "> to fix this.")
                msg = await message.channel.send(embed=em)
                sleep(2)
                await msg.delete()

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

    def multipleemojicheck(self, reaction, user):
        global messageauthor
        global checkedValue
        global custom
        newValue = checkedValue.copy()
        newValue.append("✅")
        if not custom:
            return messageauthor == user and str(reaction.emoji) in newValue
        else:
            for item in newValue:
                if str(reaction.emoji) == str(item):
                    return messageauthor == user
            return False

    def textcheck(self, message):
        global messageauthor
        global targetChannel
        return messageauthor == message.author and str(message.channel) == str(targetChannel)

    async def cancelmatchmake(self, kickmsg):
        global matchmaking
        global welcomemsg
        global msg
        global messageauthor
        member = messageauthor
        if not matchmaking:
            return False
        matchmaking = False
        if 'msg' in globals():
            await msg.delete()
        if 'welcomemsg' in globals():
            await welcomemsg.delete()
        try:
            em = discord.Embed(title="ERROR", description=kickmsg)
            await member.send(embed=em)
            await member.send(config["serverinvite"])
            await member.kick()
        except discord.errors.Forbidden:
            await self.log("ERROR\nFailed to send message to or kick user: " + str(messageauthor.name))
        return True

    async def timeout(self):
        await self.log("Timed out")
        await self.cancelmatchmake("\nTimed out! You took too long to respond to the questions (2 minutes).")

    async def matchmake(self, member):
        await self.log("Matchmaking:\n" + str(member))
        global matchmaking
        global messageauthor
        global checkedValue
        global custom
        global welcomemsg
        global msg
        if matchmaking:
            em = discord.Embed(title="ERROR", description="\nAlready matchmaking someone else, please try again soon!")
            try:
                await member.send(embed=em)
                await member.send(config["serverinvite"])
            except discord.errors.Forbidden:
                pass
            await member.kick()
            return
        if not member.bot:
            messageauthor = member
            questionSkip = 0
            totalquestions = len(config["matchmaking"]["questions"].keys())
            await self.mute(member)
            if not matchmaking:
                return
            welcomemsg = await targetChannel.send(content=member.mention + ", welcome to " + config["servername"] + ". In order to begin, please answer the following questions.")
            i = 1
            for name in config["matchmaking"]["questions"]:
                if questionSkip > 0:
                    questionSkip -= 1
                    i += 1
                    continue
                if config["matchmaking"]["questions"][name]["type"] == "submit":
                    break
                custom = False
                additions = ""
                if config["matchmaking"]["questions"][name]["questiontype"] == "multiple":
                    additions = "\n*Pick all of the below that apply, and then press the checkmark*"
                elif config["matchmaking"]["questions"][name]["reactiontype"] in ["unicode", "custom"]:
                    additions = "\n*Select an icon below that best fits the question*"
                if config["matchmaking"]["questions"][name]["reactiontype"] == "text":
                    optionlist = config["matchmaking"]["questions"][name]["answers"]
                    optionlist = await self.clean_list(optionlist, newlines=True, numbers=True)
                    additions = "\n\n*Please reply to the message with one of these options:\n" + optionlist + "*"
                em = discord.Embed(title="Question " + str(i) + "/" + str(totalquestions) + ":", description="\n" + config["matchmaking"]["questions"][name]["question"] + additions)
                msg = await targetChannel.send(embed=em)
                if config["matchmaking"]["questions"][name]["reactiontype"] == "text":
                    while True:
                        await self.log("Getting user input...")
                        role = discord.utils.get(member.guild.roles, name=config["matchmaking"]["textrole"])
                        await member.add_roles(role)
                        try:
                            usermsg = await client.wait_for('message', check=self.textcheck, timeout=120)
                        except asyncio.TimeoutError:
                            usermsg = None
                            returnval = await self.timeout()
                            if returnval:
                                break
                            if not returnval:
                                return
                        try:
                            await usermsg.delete()
                        except discord.errors.NotFound:
                            pass
                        await self.log("Recieved message: " + str(usermsg.content))
                        msgcontent = usermsg.content
                        loweranswers = []
                        for item in config["matchmaking"]["questions"][name]["answers"]:
                            loweranswers.append(item.lower())
                        indexRange = range(1, len(loweranswers) + 1)
                        answersRange = []
                        for item in indexRange:
                            answersRange.append(str(item))
                        if msgcontent.lower() in answersRange:
                            userinput = loweranswers[int(msgcontent) - 1]
                        else:
                            userinput = msgcontent.lower()
                        if userinput in loweranswers:
                            role = discord.utils.get(member.guild.roles, name=config["matchmaking"]["textrole"])
                            await member.remove_roles(role)
                            if config["matchmaking"]["questions"][name]["roles"] == 0:
                                answerIndex = loweranswers.index(userinput)
                                role = discord.utils.get(member.guild.roles, name=config["matchmaking"]["questions"][name]["answers"][answerIndex])
                                if role is not None:
                                    await member.add_roles(role)
                                break
                            else:
                                answerIndex = loweranswers.index(userinput)
                                role = discord.utils.get(member.guild.roles, name=config["matchmaking"]["questions"][name]["roles"][answerIndex])
                                if role is not None:
                                    await member.add_roles(role)
                                break
                    await msg.delete()
                    if usermsg is None:
                        msg = usermsg
                        break
                    i += 1
                    continue
                while True:
                    if config["matchmaking"]["questions"][name]["reactiontype"] == "custom":
                        custom = True
                        emojis = []
                        for emoji in config["matchmaking"]["questions"][name]["answers"]:
                            emojis.append(discord.utils.get(client.emojis, name=emoji))
                    else:
                        emojis = config["matchmaking"]["questions"][name]["answers"]
                    await self.log("Possibile Responses are:\n" + str(emojis))
                    for emoji in emojis:
                        await msg.add_reaction(emoji)
                    checkedValue = emojis
                    if config["matchmaking"]["questions"][name]["questiontype"] == "single":
                        try:
                            res = await client.wait_for('reaction_add', check=self.emojicheck, timeout=120)
                        except asyncio.TimeoutError:
                            res = None
                            returnval = await self.timeout()
                            if returnval:
                                break
                            if not returnval:
                                return
                        res = res[0]
                        answerIndex = []
                        if config["matchmaking"]["questions"][name]["reactiontype"] == "custom":
                            res = res.emoji.name
                            res = res.lower()
                        else:
                            res = res.emoji
                        if res in config["matchmaking"]["questions"][name]["answers"]:
                            answerIndex.append(config["matchmaking"]["questions"][name]["answers"].index(res))
                            await self.log("Emoji at index:\n" + str(answerIndex))
                            break
                    if config["matchmaking"]["questions"][name]["questiontype"] == "multiple":
                        await msg.add_reaction("✅")
                        response = []
                        answerIndex = []
                        while True:
                            try:
                                await self.log("Waiting for reaction...")
                                res = await client.wait_for('reaction_add', check=self.multipleemojicheck, timeout=120)
                                await self.log("Got reaction: " + str(res[0].emoji))
                                if str(res[0].emoji) == "✅":
                                    break
                                if config["matchmaking"]["questions"][name]["reactiontype"] == "custom":
                                    response.append(str(res[0].emoji.name))
                                else:
                                    response.append(str(res[0].emoji))
                            except asyncio.TimeoutError:
                                response = None
                                break
                        if response is None:
                            res = None
                            returnval = await self.timeout()
                            if returnval:
                                break
                            if not returnval:
                                return
                        for item in response:
                            answerIndex.append(config["matchmaking"]["questions"][name]["answers"].index(item))
                        break
                if res is None:
                    msg = res
                    break
                else:
                    if config["matchmaking"]["questions"][name]["type"] == "hybrid":
                        questiontype = config["matchmaking"]["questions"][name]["actionassignment"][answerIndex[0]]
                    else:
                        questiontype = config["matchmaking"]["questions"][name]["type"]
                    if questiontype == "role":
                        if config["matchmaking"]["questions"][name]["type"] == "hybrid":
                            rolelist = config["matchmaking"]["questions"][name]["actions"]
                        else:
                            rolelist = config["matchmaking"]["questions"][name]["roles"]
                        for item in answerIndex:
                            if rolelist[item] == "":
                                continue
                            role = discord.utils.get(member.guild.roles, name=rolelist[item])
                            await self.log("Assigning role:\n" + str(role))
                            await member.add_roles(role)
                    if questiontype == "action":
                        answerIndex = answerIndex[0]
                        if config["matchmaking"]["questions"][name]["actions"][answerIndex] != "":
                            actionList = config["matchmaking"]["questions"][name]["actions"][answerIndex].split()
                        if config["matchmaking"]["questions"][name]["actions"][answerIndex] == "close":
                            await msg.delete()
                            break
                        if config["matchmaking"]["questions"][name]["actions"][answerIndex] != "" and actionList[0] == "goto":
                            questionNames = config["matchmaking"]["questions"].keys()
                            increment = 0
                            gotoQuestion = 0
                            for question in questionNames:
                                if question == actionList[1]:
                                    gotoQuestion = increment
                                increment += 1
                            questionSkip = gotoQuestion - i
                            i += 1
                            await msg.delete()
                            continue
                await msg.delete()
                i += 1
            if msg is not None:
                await self.unmute(member)
                await targetChannel.send("Welcome to " + config["servername"] + ", " + member.mention + ".")
                await welcomemsg.delete()
                await self.log("Matchmaking Complete")
                if config["assignedroles"]["enabled"]:
                    await self.roleassign(member=member)

    async def on_member_join(self, member):
        global welcomemsg
        global msg
        await self.log(str(member) + " has joined the server.")
        if config["matchmaking"]["enabled"]:
            try:
                await self.matchmake(member)
            except (KeyError, discord.errors.HTTPException, AttributeError) as e:
                await self.log("ERROR\n" + str(e))
                await self.cancelmatchmake("\nSomething went wrong. Try again later.")

    async def on_member_remove(self, member):
        await self.log(str(member) + " has left the server.")
        global matchmaking
        global msg
        global welcomemsg
        global messageauthor
        if config["matchmaking"]["enabled"]:
            if matchmaking:
                if member == messageauthor:
                    matchmaking = False
                    try:
                        await welcomemsg.delete()
                        await msg.delete()
                    except NameError:
                        pass


client = roleBot()
client.run(token)
