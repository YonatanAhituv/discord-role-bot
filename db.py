import redis
import urllib.parse as urlparse
import json
import discord
import random
import string

with open('config.json', 'r') as configfile:
    config = json.loads(configfile.read())


userDict = {
    "title": "User",
    "titleMappings": {
        "roles": "Roles",
        "bio": "Bio",
    },
    "inputMappings": {
        "Change Roles": "roles",
        "Change Bio": "bio"
    },
    "typeMap": {
        "roles": "list",
        "bio": "string"
    }
}


reactionDict = {
    "title": "Reaction Limit",
    "titleMappings": {
        "reactionchannel": "Channel ID",
        "messageid": "Message ID",
        "bannedroles": "Banned Roles",
        "bypassroles": "Bypass Roles",
        "limit": "Limit"
    },
    "inputMappings": {
        "Set Channel ID": "reactionchannel",
        "Set Message ID": "messageid",
        "Change Banned Roles": "bannedroles",
        "Change Bypass Roles": "bypassroles",
        "Change Reaction Limit": "limit"
    },
    "typeMap": {
        "reactionchannel": "string",
        "messageid": "string",
        "bannedroles": "list",
        "bypassroles": "list",
        "limit": "int"
    },
}

hiddenKeys = ["everyone", "reactPass", "reactBan"]


class MyClient(discord.Client):

    async def deleteMessage(self, messageID, channel):
        try:
            msg = await channel.fetch_message(messageID)
        except (discord.errors.NotFound, discord.errors.HTTPException):
            print("Cannot find specified message")
            return
        await msg.delete()

    async def manage(self):
        info = """Welcome to Discord Bot Control.
Commands:
* !switch - Switch channels
* !delete - Delete a message
* !survey - Create a survey
* !quit - Return to main menu"""
        print(info)
        while True:
            categoryName = input("Pick a category (press ENTER if none): >>> ")
            noCat = False
            if categoryName == "":
                noCat = True
            server = client.guilds[0]
            for category in server.channels:
                if str(category.type) == "category" or noCat:
                    if category.name.lower() == categoryName.lower() or noCat:
                        while True:
                            found = False
                            channelName = input("Pick a channel: >>> ")
                            if noCat:
                                for channel in server.channels:
                                    if channel.name == channelName.lower() and channel.category_id is None:
                                        targetChannel = channel
                                        found = True
                                        break
                            else:
                                for channel in category.channels:
                                    if channelName.lower() == channel.name:
                                        targetChannel = channel
                                        found = True
                                        break
                            if found:
                                break
                        break
            while True:
                prefix = ""
                if not noCat:
                    prefix = category.name + " -> "
                userinput = input(prefix + "#" + str(targetChannel.name) + ": >>> ").replace('\\n', '\n')
                if userinput == "":
                    continue
                elif userinput == "!switch":
                    break
                elif userinput == "!leave":
                    currentGuild = None
                    for guild in client.guilds:
                        currentGuild = guild
                    await self.leave_in_protest(targetChannel, currentGuild)
                elif userinput == "!delete":
                    messageID = input("Message ID: >>> ")
                    await self.deleteMessage(messageID, targetChannel)
                elif userinput == "!survey":
                    title = input("Survey Title: >>> ")
                    i = 1
                    contents = ""
                    print("--Survey Contents--")
                    print("Type EOF when done")
                    while True:
                        userinput = input(str(i) + ": ")
                        if userinput == "EOF":
                            contents = contents[:-1]
                            break
                        contents += userinput + "\n"
                        i += 1
                    print("Comma seperate each reaction, like so: 🇦,🇧, 🇨,🇩. If you'd like to use the alphabet, place the number of letters you would like instead.")
                    while True:
                        reactions = input("Reactions: >>> ")
                        if reactions.isnumeric():
                            reactions = int(reactions)
                            reactions = ["🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯", "🇰", "🇱", "🇲", "🇳", "🇴", "🇵", "🇶", "🇷", "🇸", "🇹"][:reactions]
                            break
                        else:
                            reactions = reactions.split(',')
                            if len(reactions) > 0:
                                break
                            else:
                                print("Invalid Input!")
                    while True:
                        userinput = input("Would you like to place reaction limits on this survey? [Y/n]: >>> ")
                        if userinput.lower() == "y":
                            reactionLimits = True
                            break
                        elif userinput.lower() == "n":
                            reactionLimits = False
                            break
                    em = discord.Embed(title=title, description=contents)
                    msg = await targetChannel.send(embed=em)
                    for emoji in reactions:
                        await msg.add_reaction(emoji)
                    if reactionLimits:
                        while True:
                            title = "Survey: "
                            for item in range(1, 10):
                                title += random.choice(string.ascii_letters)
                            if item not in redisKeys():
                                break
                        reactionLimit = {
                            "reactionchannel": str(msg.channel.id),
                            "messageid": str(msg.id)

                        }
                        r.hmset(title, reactionLimit)
                        modify(title, reactionDict)
                elif userinput == "!quit":
                    await client.logout()
                else:
                    if "@" in userinput:
                        mentionSplitList = userinput.split(" ")
                        mentionList = []
                        for word in mentionSplitList:
                            if word[0] == "@":
                                mentionList.append(word)
                        for mention in mentionList:
                            for member in client.guilds[0].members:
                                if mention.replace("@", "").lower() == member.name.split("#", 3)[0].lower() or mention.replace("@", "").lower() == str(member.nick).split("#", 3)[0].lower():
                                    userinput = userinput.replace(mention, "<@" + str(member.id) + ">")
                                    break
                    await targetChannel.send(userinput)

    async def on_ready(self):
        print('Logged in as ' + self.user.name)
        await self.manage()


def redisInit():
    url = urlparse.urlparse(config["redis"]["url"])
    if url.port is None:
        port = config["redis"]["port"]
    else:
        port = url.port
    if url.password is None:
        password = config["redis"]["password"]
    else:
        password = url.password
    r = redis.Redis(host=url.hostname, port=port, password=password)
    return r


def indexDataProcessor(keys, userinput):
    indexes = list(range(1, len(keys) + 1))
    targetitem = ""
    indexes = [str(val) for val in indexes]
    if userinput.lower() in indexes:
        i = 1
        for item in keys:
            if i == int(userinput):
                targetitem = str(item)
            i += 1
    elif userinput.lower() in [val.lower() for val in keys]:
        for item in keys:
            if item.lower() == userinput.lower():
                targetitem = str(item)
    return targetitem


def indexinputs(keys, infomsg, msg):
    indexes = list(range(1, len(keys) + 1))
    print(infomsg)
    i = 1
    for item in keys:
        print(str(i) + ": " + str(item))
        i += 1
    userinput = input(msg)
    keys = [val.lower() for val in keys]
    indexes = [str(val) for val in indexes]
    if userinput.lower() in keys or userinput in indexes:
        return True, userinput
    else:
        return False, userinput


def optionfield(keys):
    return indexinputs(keys, "Your options are:", "Pick an option: >>> ")


def stringListToList(ilist):
    return json.loads(ilist.replace("'", '"'))


def modifyString(title, string=""):
    print()
    if string != "":
        print("The current value is: " + str(string))
    string = input("Set " + title + " To: >>> ")
    return string


def modifyInt(title, number=-1):
    print()
    if number != -1:
        print("The current value is: " + str(number))
    while True:
        number = input("Set " + title + " To: >>> ")
        if number.isnumeric():
            number = int(number)
            break
        else:
            print("That is not a number!")
    return number


def modifyList(title, targetList=[]):
    while True:
        print()
        print(title + ": " + str(targetList))
        keys = ["Add", "Set", "Delete", "Save and Quit"]
        done = False
        while not done:
            done, userinput = optionfield(keys)
        userinput = indexDataProcessor(keys, userinput)
        if userinput.lower() == "add":
            userinput = input("New Item: >>> ")
            targetList.append(userinput)
        elif userinput.lower() == "set":
            while True:
                userinput = input("New List: >>> ")
                try:
                    userinput = stringListToList(userinput)
                    break
                except json.decoder.JSONDecodeError:
                    print("Invalid List! Try again.")
            targetList = userinput
        elif userinput.lower() == "delete":
            done = False
            while not done:
                done, userinput = indexinputs(targetList, "Your options are: ", "Pick an item to delete: >>> ")
                userinput = indexDataProcessor(targetList, userinput)
                if userinput in targetList:
                    targetindex = targetList.index(userinput)
                    del targetList[targetindex]
                else:
                    done = False
        elif userinput.lower() == "save and quit":
            return targetList


def dictToUTF8(dictonary):
    finaldict = {}
    for value in dictonary:
        finaldict[str(value, 'utf-8')] = str(dictonary[value], 'utf-8')
    return finaldict


def modify(targetitem, metaDict, new=False):
    if not new:
        finaldict = getDict(targetitem)
    elif new:
        finaldict = {}
    while True:
        done = False
        print()
        if not finaldict == {}:
            print(metaDict["title"] + " Contents:")
            for value in finaldict:
                print(str(metaDict["titleMappings"][value]) + ": " + str(finaldict[value]))
        keys = list(metaDict["inputMappings"].keys())
        keys.append("Delete")
        keys.append("Quit")
        while not done:
            done, userinput = optionfield(keys)
        userinput = indexDataProcessor(keys, userinput)
        if userinput in metaDict["inputMappings"]:
            selectedItem = metaDict["inputMappings"][userinput]
            targetType = metaDict["typeMap"][selectedItem]
            itemTitle = metaDict["titleMappings"][selectedItem]
            if targetType == "list":
                if selectedItem in finaldict.keys():
                    finaldict[selectedItem] = str(modifyList(itemTitle, stringListToList(finaldict[selectedItem])))
                else:
                    finaldict[selectedItem] = str(modifyList(itemTitle))
                newdict = getDict(selectedItem)
                newdict[selectedItem] = str(finaldict[selectedItem])
                r.hmset(targetitem, newdict)
            elif targetType == "string":
                if selectedItem in finaldict.keys():
                    finaldict[selectedItem] = modifyString(itemTitle, finaldict[selectedItem])
                else:
                    finaldict[selectedItem] = modifyString(itemTitle)
                newdict = getDict(targetitem)
                newdict[selectedItem] = finaldict[selectedItem]
                r.hmset(targetitem, newdict)
            elif targetType == "int":
                if selectedItem in finaldict.keys():
                    finaldict[selectedItem] = modifyInt(itemTitle, finaldict[selectedItem])
                else:
                    finaldict[selectedItem] = modifyInt(itemTitle)
                newdict = getDict(targetitem)
                newdict[selectedItem] = finaldict[selectedItem]
                r.hmset(targetitem, newdict)
        elif userinput.lower() == "delete":
            if finaldict == {}:
                print("ERROR: Cannot delete an empty item")
            else:
                while True:
                    userinput = input("Are you sure (y/n)? >>> ")
                    if userinput.lower() == "y":
                        r.delete(targetitem)
                        print("Deleted: " + str(targetitem) + "...")
                        return
                    if userinput.lower() == "n":
                        print("Deletion Canceled")
                        break
        elif userinput.lower() == "quit":
            return


def getDict(key):
    data = r.hgetall(key)
    item = dictToUTF8(data)
    return item


def redisKeys():
    keys = []
    for option in r.keys():
        keys.append(str(option, 'utf-8'))
    return keys


def select():
    while True:
        keys = redisKeys()
        keys = [x for x in keys if x not in hiddenKeys]
        print()
        print("You have " + str(len(keys)) + " item(s) in the database.")
        keys.append("Quit")
        done = False
        while not done:
            done, userinput = optionfield(keys)
        targetitem = indexDataProcessor(keys, userinput)
        if targetitem.lower() == "quit":
            print()
            return
        # Wish there was a better way to do this but Redis is complete garbage
        if len(targetitem) == 18 and targetitem.isnumeric():
            modify(targetitem, userDict)
        else:
            modify(targetitem, reactionDict)


def add():
    keys = ["User", "Reaction Limit", "Quit"]
    done = False
    while not done:
        done, userinput = optionfield(keys)
    itemType = indexDataProcessor(keys, userinput)
    if itemType.lower() == "user":
        while True:
            userinput = input("Enter the user ID you would like to put in the database: >>> ")
            if not userinput.isnumeric() or not len(userinput) == 18:
                print("Enter a valid user ID!")
                continue
            modify(str(userinput), userDict, new=True)
    elif itemType.lower() == "reaction limit":
        while True:
            userinput = input("Enter a descriptive title: >>> ")
            if userinput in hiddenKeys:
                print("That name cannot be used!")
                continue
            modify(str(userinput), reactionDict, new=True)
            break
    else:
        return


def getPolls():
    keys = redisKeys()
    polls = {}
    for item in keys:
        if not len(item) == 18 and not item.isnumeric() and item not in hiddenKeys:
            itemDict = getDict(item)
            item = {item: itemDict}
            polls.update(item)
    return polls


def getList(key):
    rolelist = r.get(key)
    rolelist = stringListToList(str(rolelist, 'utf-8'))
    return rolelist


def enforceRoles():
    keys = ["Enforce Roles", "Enforce Role Permissions", "Quit"]
    done = False
    while not done:
        done, userinput = optionfield(keys)
    userinput = indexDataProcessor(keys, userinput)
    if userinput.lower() == "enforce roles":
        if "everyone" in redisKeys():
            rolelist = getList("everyone")
        else:
            rolelist = []
        r.set("everyone", str(modifyList("Enforced Roles", rolelist)))
        print()
    elif userinput.lower() == "enforce role permissions":
        keys = ["Ban Roles from Reacting", "Allow Roles through Banned Role Limits", "Quit"]
        done = False
        while not done:
            done, userinput = optionfield(keys)
        userinput = indexDataProcessor(keys, userinput)
        if userinput.lower() == "ban roles from reacting":
            if "reactBan" in redisKeys():
                roleList = getList("reactBan")
            else:
                roleList = []
            r.set("reactBan", str(modifyList("Banned Roles", roleList)))
            print()
        elif userinput.lower() == "allow roles through banned role limits":
            if "reactPass" in redisKeys():
                roleList = getList("reactPass")
            else:
                roleList = []
            r.set("reactPass", str(modifyList("Passthrough Roles", roleList)))
            print()
    else:
        return


def welcome():
    while True:
        print("---Welcome to Discord Role Managment Bot Control Panel!---")
        keys = ["Modify", "Add", "Enforce Roles", "Control Bot", "Quit"]
        done = False
        while not done:
            done, userinput = optionfield(keys)
        targetitem = indexDataProcessor(keys, userinput)
        if targetitem.lower() == "modify":
            select()
        elif targetitem.lower() == "add":
            add()
        elif targetitem.lower() == "enforce roles":
            enforceRoles()
        elif targetitem.lower() == "control bot":
            token = config["token"]
            client.run(token)
        elif targetitem.lower() == "quit":
            return


r = redisInit()
if __name__ == "__main__":
    intents = discord.Intents(messages=True, guilds=True, members=True, bans=True, emojis=True, integrations=True, webhooks=True, invites=True, voice_states=True, presences=True, guild_messages=True, dm_messages=True, reactions=True, guild_reactions=True, dm_reactions=True, typing=True, guild_typing=True, dm_typing=True)
    client = MyClient(intents=intents)
    welcome()
