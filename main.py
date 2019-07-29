import discord
import json
from time import sleep

with open('data.json', 'r') as datafile:
    data = json.loads(datafile.read())

token = data["token"]

global targetChannel

matchmaking = False

class MyClient(discord.Client):

    async def removebotroles(self, member: discord.Member):
        print(str(member))
        roles = []
        print("Clearing all bot assigned roles...")
        for items in data["questions"]:
            print(str(items))
            try:
                if data["questions"][items]["roles"] == 0:
                    rolelist = data["questions"][items]["answers"]
                else:
                    rolelist = data["questions"][items]["roles"]
                for item in rolelist:
                    if item != "":
                        roles.append(item)
            except KeyError:
                pass
        print(str(roles))
        print("Got list of all roles, and removing them from member now...")
        rolestodelete = []
        for role in member.roles:
            if role.name in rolelist:
                rolestodelete.append(role)
        for role in rolestodelete:
            await client.remove_roles(member, role)
        print("Done!")

    async def mute(self, member: discord.Member):
        global matchmaking
        matchmaking = True
        role = discord.utils.get(member.server.roles, name=data["newrole"])
        await client.add_roles(member, role)
        try:
            await self.removebotroles(member)
        except:
            matchmaking = False

    async def unmute(self, member: discord.Member):
        global matchmaking
        matchmaking = False
        role = discord.utils.get(member.server.roles, name=data["newrole"])
        await client.remove_roles(member, role)

    async def on_ready(self):
        print()
        print('-' * len(str(self.user.id)))
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('-' * len(str(self.user.id)))
        print()
        global matchmaking
        matchmaking = False
        # Do not run this unless you are 1000% sure what you are doing
        # servers = list(client.servers)
        # for server in servers:
        #     for member in server.members:
        #         await self.removebotroles(member)
        for server in client.servers:
            for channel in server.channels:
                if channel.name == data["targetchannels"]["welcome"]:
                    global targetChannel
                    targetChannel = channel
                    print("-" * len(str(targetChannel.id)))
                    print("Found " + targetChannel.name)
                    print(str(targetChannel.id))
                    print("-" * len(str(targetChannel.id)))
                    print()
                if channel.name == data["targetchannels"]["complaints"]:
                    global complaintsChannel
                    complaintsChannel = channel
                    print("-" * len(str(complaintsChannel.id)))
                    print("Found " + complaintsChannel.name)
                    print(str(complaintsChannel.id))
                    print("-" * len(str(complaintsChannel.id)))
                    print()

    async def clean_list(self, finput, newlines=False):
        print("Cleaning list...")
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

    async def on_message(self, message):
        global matchmaking
        highestlen = 0
        msglist = ["From: " + str(message.author), "Sent in: " + str(message.author.server) + " in #" + str(message.channel), "Content: " + str(message.content)]
        for msg in msglist:
            if len(msg) > highestlen:
                highestlen = len(msg)
        print("-" * highestlen)
        for msg in msglist:
            print(msg)
        print("-" * highestlen)
        if message.content == "!matchmake":
            if not matchmaking:
                await client.delete_message(message)
                statusmsg = await client.send_message(message.channel, "Matchmaking " + message.author.mention + "...")
                await self.matchmake(message.author)
                await client.delete_message(statusmsg)
            else:
                em = discord.Embed(title="ERROR", description="\nAlready matchmaking someone else, please try again soon!")
                await client.send_message(message.channel, embed=em)
        elif message.content == "!roleassign":
            await self.roleassign(message=message)
        else:
            msglist = message.content.split()
            if len(msglist) > 0 and msglist[0] == "!complain":
                await self.complain(message)

    async def complain(self, message):
        complaint = message.content.replace("!complain ", "")
        await client.delete_message(message)
        em = discord.Embed(title="Success", description="\nComplaint has been sent to moderators!")
        msg = await client.send_message(message.channel, embed=em)
        em = discord.Embed(title="Complaint Recieved", description="\n" + str(complaint))
        await client.send_message(complaintsChannel, embed=em)
        sleep(2)
        await client.delete_message(msg)

    async def roleassign(self, member=None, message=None):
        if message is not None:
            member = message.author
        membername = str(member)
        print(data["assignedroles"].keys())
        print(membername)
        if membername in data["assignedroles"].keys():
            for role in data["assignedroles"][membername]:
                role = discord.utils.get(member.server.roles, name=role)
                await client.add_roles(member, role)
            if message is not None:
                print("Assigning roles...")
                rolelist = data["assignedroles"][membername]
                rolelist = await self.clean_list(rolelist)
                em = discord.Embed(title="Success", description="\nAssigned the following roles: " + rolelist + ".")
                await client.send_message(message.channel, embed=em)
        else:
            if message is not None:
                await client.send_message(message.channel, "Failed to assign roles, please contact " + "<@" + data["admintoken"] + "> to fix this.")

    async def matchmake(self, member):
        print(str(member))
        global matchmaking
        if matchmaking:
            em = discord.Embed(title="ERROR", description="\nAlready matchmaking someone else, please try again soon!")
            await client.send_message(member, embed=em)
            await client.send_message(member, data["serverinvite"])
            await client.kick(member)
            return
        if not member.bot:
            totalquestions = len(data["questions"].keys())
            await self.mute(member)
            if not matchmaking:
                return
            welcomemsg = await client.send_message(targetChannel, member.mention + ", welcome to " + data["servername"] + ". In order to begin, please answer the following questions.")
            i = 1
            for name in data["questions"]:
                additions = ""
                if data["questions"][name]["reactiontype"] == "text":
                    optionlist = data["questions"][name]["answers"]
                    optionlist = await self.clean_list(optionlist, newlines=True)
                    additions = "\n\nPlease reply to the message with one of these options:\n" + optionlist
                em = discord.Embed(title="Question " + str(i) + "/" + str(totalquestions) + ":", description="\n" + data["questions"][name]["question"] + additions)
                msg = await client.send_message(targetChannel, embed=em)
                if data["questions"][name]["reactiontype"] == "text":
                    while True:
                        print("Getting user input...")
                        role = discord.utils.get(member.server.roles, name=data["textrole"])
                        await client.add_roles(member, role)
                        usermsg = await client.wait_for_message(author=member, timeout=120)
                        # print(str(usermsg.content))
                        if usermsg is None:
                            print("Timed out")
                            await client.send_message(member, "Timed out, rejoin " + data["servername"] + " to try again.")
                            await client.send_message(member, data["serverinvite"])
                            await client.delete_message(welcomemsg)
                            await client.kick(member)
                            break
                        msgcontent = usermsg.content
                        loweranswers = []
                        for item in data["questions"][name]["answers"]:
                            loweranswers.append(item.lower())
                        if msgcontent.lower() in loweranswers:
                            role = discord.utils.get(member.server.roles, name=data["textrole"])
                            await client.remove_roles(member, role)
                            if data["questions"][name]["roles"] == 0:
                                answerIndex = loweranswers.index(msgcontent.lower())
                                print("Roles is set to 0")
                                role = discord.utils.get(member.server.roles, name=data["questions"][name]["answers"][answerIndex])
                                await client.add_roles(member, role)
                                print("Role assigned")
                                break
                            else:
                                answerIndex = loweranswers.index(msgcontent)
                                role = discord.utils.get(member.server.roles, name=data["questions"][name]["roles"][answerIndex])
                                await client.add_roles(member, role)
                                break

                    await client.delete_message(usermsg)
                    await client.delete_message(msg)
                    if msg is None:
                        break
                    i += 1
                    continue
                while True:
                    if data["questions"][name]["reactiontype"] == "custom":
                        emojis = []
                        for emoji in data["questions"][name]["answers"]:
                            emojis.append(discord.utils.get(client.get_all_emojis(), name=emoji))
                    else:
                        emojis = data["questions"][name]["answers"]
                    for emoji in emojis:
                        await client.add_reaction(msg, emoji)
                    res = await client.wait_for_reaction(emojis, user=member, message=msg, timeout=120)
                    if res is None:
                        await client.send_message(member, "Timed out, rejoin " + data["servername"] + " to try again.")
                        await client.send_message(member, data["serverinvite"])
                        await client.kick(member)
                        await client.delete_message(msg)
                        await client.delete_message(welcomemsg)
                        break
                    if data["questions"][name]["reactiontype"] == "custom":
                        res = res.reaction.emoji.name
                        res = res.lower()
                    else:
                        res = res.reaction.emoji
                    if res in data["questions"][name]["answers"]:
                        answerIndex = data["questions"][name]["answers"].index(res)
                        print("Emoji at index:", str(answerIndex))
                        break
                if msg is None:
                    break
                else:
                    if data["questions"][name]["type"] == "role" and data["questions"][name]["roles"][answerIndex] != "":
                        role = discord.utils.get(member.server.roles, name=data["questions"][name]["roles"][answerIndex])
                        print(str(role))
                        await client.add_roles(member, role)
                    if data["questions"][name]["type"] == "action":
                        if data["questions"][name]["actions"][answerIndex] == "close":
                            await client.delete_message(msg)
                            break
                await client.delete_message(msg)
                i += 1
            if msg is not None:
                await self.unmute(member)
                await client.send_message(targetChannel, "Welcome to " + data["servername"] + ", " + member.mention + ".")
                await client.delete_message(welcomemsg)
                await self.roleassign(member=member)

    async def on_member_join(self, member):
        await self.matchmake(member)

client = MyClient()
client.run(token)