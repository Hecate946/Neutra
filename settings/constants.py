from utilities import utils

config = utils.config().copy()

token = config["token"]
tester = config["tester"]
postgres = config["postgres"]
github = config["github"]
support = config["support"]
avchan = config["avchan"]
botlog = config["botlog"]
embed = config["embed"]
home = config["home"]
bitly = config["bitly"]
timezonedb = config["timezonedb"]
prefix = config["prefix"]
owners = config["owners"]
admins = config["admins"]

emotes = {
    "loading": "<a:loading:819280509007560756>",
    "success": "<:checkmark:816534984676081705>",
    "failed": "<:failed:816521503554273320>",
    "warn": "<:warn:816456396735905844>",
    "error": "<:error:836325837871382638>",
    "announce": "<:announce:834495346058067998>",
    "1234button": "<:1234:816460247777411092>",
    "info": "<:info:827428282001260544>",
    "exclamation": "<:exclamation:827753511395000351>",
    "trash": "<:trash:816463111958560819>",
    "forward": "<:forward:816458167835820093>",
    "forward2": "<:forward2:816457685905440850>",
    "backward": "<:backward:816458218145579049>",
    "backward2": "<:backward2:816457785167314987>",
    "desktop": "<:desktop:817160032391135262>",
    "mobile": "<:mobile:817160232248672256>",
    "web": "<:web:817163202877194301>",
    "online": "<:online:810650040838258711>",
    "offline": "<:offline:810650959859810384>",
    "dnd": "<:dnd:810650845007708200>",
    "idle": "<:idle:810650560146833429>",
    "owner": "<:owner:810678076497068032>",
    "emoji": "<:emoji:810678717482532874>",
    "categories": "<:categories:810671569440473119>",
    "textchannel": "<:textchannel:810659118045331517>",
    "voicechannel": "<:voicechannel:810659257296879684>",
    "messages": "<:messages:816696500314701874>",
    "commands": "<:command:816693906951372870>",
    "role": "<:role:816699853685522442>",
    "invite": "<:invite:816700067632513054>",
    "bot": "<:bot:816692223566544946>",
    "question": "<:question:817545998506393601>",
    "lock": "<:lock:817168229712527360>",
    "unlock": "<:unlock:817168258825846815>",
    "letter": "<:letter:816520981396193280>",
    "num0": "<:num0:827219939583721513>",
    "num1": "<:num1:827219939961602098>",
    "num2": "<:num2:827219940045226075>",
    "num3": "<:num3:827219940541071360>",
    "num4": "<:num4:827219940556931093>",
    "num5": "<:num5:827219941253709835>",
    "num6": "<:num6:827219941790580766>",
    "num7": "<:num7:827219942343442502>",
    "num8": "<:num8:827219942444236810>",
    "num9": "<:num9:827219942758809610>",
    "stop": "<:stop:827257105420910652>",
    "clock": "<:clock:839640961755643915>",
    "alarm": "<:alarm:839640804246683648>",
    "stopwatch": "<:stopwatch:827075158967189544>",
    "log": "<:log:835203679388303400>",
    "db": "<:database:839574200506646608>",
    "privacy": "<:privacy:839574405541134346>",
    "delete": "<:deletedata:839587782091735040>",
    "heart": "<:heart:839354647546298399>",
}
