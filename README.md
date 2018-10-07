# Athena-Cogs
Random cogs I have created for [Red-DiscordBot](https://github.com/Cog-Creators/Red-DiscordBot).

## Working Cogs
These are at a point where you can actually use them.
* chatterbot - Uses the [ChatterBot](https://github.com/gunthercox/ChatterBot) module to implement a learning chatbot.
* inspire - Generate inspiration quotes using [InspiroBot](http://inspirobot.me).
* kankaview - Access your [Kanka](https://kanka.io/en/campaign/985) campaigns from Discord.
* quake - Pulls information on recent earthquakes from [GeoNet](https://www.geonet.org.nz).

## Broken cogs
These are unfinished, abandoned or otherwise unusable cogs.
* mafia - Runs a game of [mafia](https://en.wikipedia.org/wiki/Mafia_(party_game)).

## Installation Notes
### General
I haven't gotten around to applying for cogs.red listing yet so you won't be able to install them through there. Instead you'll want to run these two commands:
1. `[p]cog repo add Athena-Cogs https://github.com/arconyx/Athena-Cogs`
2. `[p]cog install Athena-Cogs <cogname>`

### ChatterBot
Be aware that it currently only works with the ! command prefix (I haven't gotten around to fixing that), requires MongoDB to be running and records all messages sent (in channels it isn't set to ignore) to a MongoDB database. Also, the bot does not distinguish between server - messages learnt in one server could be repeated in any server it is in.

### KankaView
For this to work you'll need an Personal Access Token for Kanka. You can get this on your profile page, but you will need to contact the dev for API permissions first. Set the token using `!kankaset token <token>` after installing this cog.
