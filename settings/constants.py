from utilities import utils

config = utils.config()
try:
    admins = config["admins"]
    bitly = config["bitly"]
    embed = config["embed"]
    gtoken = config["gtoken"]
    owners = config["owners"]
    postgres = config["postgres"]
    prefix = config["prefix"]
    support = config["support"]
    tester = config["tester"]
    timezonedb = config["timezonedb"]
    token = config["token"]
except KeyError as e:
    print(
        f"""
          Warning! The key {e} is missing from your ./config.json file.
          Add this key or the bot might not function properly.
          """
    )
avatars = {
    "red": "https://cdn.discordapp.com/attachments/846597178918436885/847339918216658984/red.png",
    "orange": "https://cdn.discordapp.com/attachments/846597178918436885/847342151238811648/orange.png",
    "yellow": "https://cdn.discordapp.com/attachments/846597178918436885/847341423945711637/yellow.png",
    "green": "https://cdn.discordapp.com/attachments/846597178918436885/847528287739314176/green.png",
    "blue": "https://cdn.discordapp.com/attachments/846597178918436885/847339750042239007/blue.png",
    "purple": "https://cdn.discordapp.com/attachments/846597178918436885/847340695823450117/purple.png",
    "black": "https://cdn.discordapp.com/attachments/846597178918436885/847339605555675176/black.png",
}
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
    "search": "<:web:817163202877194301>",
    "online": "<:online:810650040838258711>",
    "offline": "<:offline:810650959859810384>",
    "dnd": "<:dnd:810650845007708200>",
    "idle": "<:idle:810650560146833429>",
    "owner": "<:owner:810678076497068032>",
    "emoji": "<:emoji:810678717482532874>",
    "members": "<:members:810677596453863444>",
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
    "stopsign": "<:stopsign:841848010690658335>",
    "clock": "<:clock:839640961755643915>",
    "alarm": "<:alarm:839640804246683648>",
    "stopwatch": "<:stopwatch:827075158967189544>",
    "log": "<:log:835203679388303400>",
    "db": "<:database:839574200506646608>",
    "privacy": "<:privacy:839574405541134346>",
    "delete": "<:deletedata:839587782091735040>",
    "heart": "<:heart:839354647546298399>",
    "graph": "<:graph:840046538340040765>",
    "upload": "<:upload:840086768497983498>",
    "download": "<:download:840086726209961984>",
    "right": "<:right:840289355057725520>",
    "kick": "<:kick:840490315893702667>",  # So its a she 💞
    "ban": "<:ban:840474680547606548>",
    "robot": "<:robot:840482243218767892>",
    "plus": "<:plus:840485455333294080>",
    "minus": "<:minus:840485608555020308>",
    "undo": "<:undo:840486528110166056>",
    "redo": "<:redo:840486303354322962>",
    "audioadd": "<:audioadd:840491464928002048>",
    "audioremove": "<:audioremove:840491410720948235>",
    "pin": "<:pin:840492943226961941>",
    "pass": "<:pass:840817730277867541>",
    "fail": "<:fail:840817815148953600>",
    "snowflake": "<:snowflake:841848061412376596>",
}
