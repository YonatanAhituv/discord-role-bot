import redis
import urllib.parse as urlparse
import json


def redisInit():
    with open('config.json', 'r') as configfile:
        config = json.loads(configfile.read())
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
    try:
        if int(userinput) in indexes:
            i = 1
            targetitem = ""
            for item in keys:
                if i == int(userinput):
                    targetitem = str(item)
                i += 1
    except ValueError:
        if userinput in keys:
            targetitem = ""
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
    try:
        intinput = int(userinput)
    except ValueError:
        intinput = False
    if userinput.lower() in keys or intinput in indexes:
        return True, userinput
    else:
        return False, userinput


def optionfield(keys):
    return indexinputs(keys, "Your options are:", "Pick an option: >>> ")


def stringListToList(ilist):
    return json.loads(ilist.replace("'", '"'))


def modifybio(bio=""):
    print()
    if bio != "":
        print("The current bio is: " + str(bio))
    bio = input("Set Bio To: >>> ")
    return bio


def modifyroles(rolelist=[]):
    while True:
        print()
        print("Roles: " + str(rolelist))
        keys = ["Add", "Set", "Delete", "Save and Quit"]
        done = False
        while not done:
            done, userinput = optionfield(keys)
        userinput = indexDataProcessor(keys, userinput)
        if userinput.lower() == "add":
            userinput = input("New Role: >>> ")
            rolelist.append(userinput)
        elif userinput.lower() == "set":
            while True:
                userinput = input("New Role List: >>> ")
                try:
                    userinput = stringListToList(userinput)
                    break
                except json.decoder.JSONDecodeError:
                    print("Invalid List! Try again.")
            rolelist = userinput
        elif userinput.lower() == "delete":
            done = False
            while not done:
                done, userinput = indexinputs(rolelist, "Your options are: ", "Pick a role to delete: >>> ")
            userinput = indexDataProcessor(rolelist, userinput)
            targetindex = rolelist.index(userinput)
            del rolelist[targetindex]
        elif userinput.lower() == "save and quit":
            return rolelist


def dictToUTF8(dictonary):
    finaldict = {}
    for value in dictonary:
        finaldict[str(value, 'utf-8')] = str(dictonary[value], 'utf-8')
    return finaldict


def modify(targetitem, new=False):
    if not new:
        finaldict = getMember(targetitem)
    elif new:
        finaldict = {}
    while True:
        done = False
        print()
        if not finaldict == {}:
            print("User Contents:")
            for value in finaldict:
                print(str(value).capitalize() + ": " + str(finaldict[value]))
        keys = ["Change Roles", "Change Bio", "Delete", "Quit"]
        while not done:
            done, userinput = optionfield(keys)
        userinput = indexDataProcessor(keys, userinput)
        if userinput.lower() == "change roles":
            if "roles" in finaldict.keys():
                finaldict["roles"] = modifyroles(stringListToList(finaldict["roles"]))
            else:
                finaldict["roles"] = modifyroles()
            newdict = getMember(targetitem)
            newdict["roles"] = str(finaldict["roles"])
            r.hmset(targetitem, newdict)
        elif userinput.lower() == "change bio":
            if "bio" in finaldict.keys():
                finaldict["bio"] = modifybio(finaldict["bio"])
            else:
                finaldict["bio"] = modifybio()
            newdict = getMember(targetitem)
            newdict["bio"] = finaldict["bio"]
            r.hmset(targetitem, newdict)
        if userinput.lower() == "delete":
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


def getMember(key):
    data = r.hgetall(key)
    user = dictToUTF8(data)
    return user


def redisKeys():
    keys = []
    for option in r.keys():
        keys.append(str(option, 'utf-8'))
    return keys


def select():
    while True:
        print()
        print("You have " + str(len(r.keys())) + " user(s) in the database.")
        keys = redisKeys()
        if "everyone" in keys:
            keys.remove("everyone")
        keys.append("Quit")
        done = False
        while not done:
            done, userinput = optionfield(keys)
        targetitem = indexDataProcessor(keys, userinput)
        if targetitem.lower() == "quit":
            print()
            return
        modify(targetitem)


def add():
    userinput = input("Enter the user ID you would like to put in the database: >>> ")
    modify(str(userinput), new=True)


def getList(key):
    rolelist = r.get(key)
    rolelist = stringListToList(str(rolelist, 'utf-8'))
    return rolelist


def everyoneroles():
    if "everyone" in redisKeys():
        rolelist = getList("everyone")
    else:
        rolelist = []
    r.set("everyone", str(modifyroles(rolelist)))
    print()


def welcome():
    while True:
        print("---Welcome to Discord Role Managment Bot Control Panel!---")
        keys = ["Modify", "Add", "Enforce Roles", "Quit"]
        done = False
        while not done:
            done, userinput = optionfield(keys)
        targetitem = indexDataProcessor(keys, userinput)
        if targetitem.lower() == "modify":
            select()
        elif targetitem.lower() == "add":
            add()
        elif targetitem.lower() == "enforce roles":
            everyoneroles()
        elif targetitem.lower() == "quit":
            return


r = redisInit()
if __name__ == "__main__":
    welcome()
