# A file responsible for storing bot data.
import os, json, asyncio, time, math
import defaultdata
import talkingstreak, qotd

activedata = dict()

class DataStore():
    def __init__(self):
        self.datafolder = "data"
        self.userdatafolder = "userdata"
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.makedirs(os.path.join(script_dir, self.datafolder), exist_ok=True)
        os.makedirs(os.path.join(script_dir, self.userdatafolder), exist_ok=True)

    
    def reconsile(self, data):
        if data:
            for i in defaultdata.defaultdata.keys():
                if not i in data:
                    data[i] = defaultdata.defaultdata[i]
                elif isinstance(defaultdata.defaultdata[i], dict):
                    for j in defaultdata.defaultdata[i].keys():
                        if not j in data[i]:
                            data[i][j] = defaultdata.defaultdata[i][j]
            return data
        else:
            return defaultdata.defaultdata.copy()

    def getpath(self, ID):
        return os.path.join(os.path.join(os.path.dirname(os.path.abspath(__file__)), self.datafolder), f'{ID}.json')

    def createdata(self, ID):
        thingpath = self.getpath(ID)
        if not os.path.exists(thingpath):
            with open(thingpath, "w") as file:
                json.dump(defaultdata.defaultdata, file, indent=4)
            activedata[ID] = defaultdata.defaultdata.copy()
            print(f"Added data for new guild: {ID}")
        elif not ID in activedata:
            with open(thingpath, "r") as file:
                file = json.load(file)
                file = self.reconsile(file)
                activedata[ID] = file
                activedata[ID]["guild_id"] = int(ID)
                if file["modulesenabled"]["talkstreak"]:
                    if file["talkstreak"]["settings"]["set_fail_time"]:
                        for i, v in file["talkstreak"]["cd_check"].items():
                            if v + file["talkstreak"]["cooldown"] < time.time():
                                file["talkstreak"]["cd_check"][i] = math.ceil(time.time()) - file["talkstreak"]["cooldown"]
                    asyncio.create_task(talkingstreak.professional_rifle_hanger(file))
                if file["modulesenabled"]["qotd"]:
                    for i in file["qotd"]["decks"].values():
                        asyncio.create_task(qotd.hang_a_rifle(file, i))
                

    def destroydata(self, ID):
        path = self.getpath(ID)
        if os.path.exists(path):
            os.remove(path)

    def getdata(self, ID):
        self.createdata(ID)
        return activedata[ID]

    def save(self, ID, data):
        with open(self.getpath(ID), "w") as file:
            json.dump(data, file, indent=4)

    # -- USER SETTINGS --

    def getuserpath(self, ID):
        return os.path.join(os.path.join(os.path.dirname(os.path.abspath(__file__)), self.userdatafolder), f'{ID}.json')
    
    def setsetting(self, ID, i, v):
        thingpath = self.getuserpath(ID)
        if not os.path.exists(thingpath):
            with open(thingpath, "w") as file:
                json.dump({i: v}, file, indent=4)
        else:
            with open(thingpath, "r") as file:
                k = json.load(file)
            with open(thingpath, "w") as file:
                k[i] = v
                json.dump(k, file, indent=4)
    
    def getsetting(self, ID, i):
        thingpath = self.getuserpath(ID)
        if os.path.exists(thingpath):
            with open(thingpath, "r") as file:
                k = json.load(file)
                if i in k:
                    return k[i]
        return defaultdata.defaultsettings[i]

datastore = DataStore()

async def autosave():
    while True:
        for ID, data in activedata.items():
            try:
                datastore.save(ID, data)
            except Exception as e:
                print(f"Saving {ID} failed for the reason of {e}")
        await asyncio.sleep(40)