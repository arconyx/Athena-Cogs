# Athena-Cogs
Random cogs I have created for [Red-DiscordBot](https://github.com/Cog-Creators/Red-DiscordBot).

## Working Cogs
These are at a point where you can actually use them.
* chatterbot - Uses the [ChatterBot](https://github.com/gunthercox/ChatterBot) module to implement a learning chatbot.
* inspire - Generate inspiration quotes using [InspiroBot](http://inspirobot.me).
* kankaview - Access your [Kanka](https://kanka.io) campaigns from Discord.
* quake - Pulls information on recent earthquakes from [GeoNet](https://www.geonet.org.nz).

## Broken cogs
These are unfinished, abandoned or otherwise unusable cogs.
* mafia - Runs a game of [mafia](https://en.wikipedia.org/wiki/Mafia_(party_game)).

## Installation Notes
### General
I haven't gotten around to applying for cogs.red listing yet so you won't be able to install them through there. Instead you'll want to run these two commands (`[p]` should be replaced with the bot's command prefix):
1. `[p]load downloader`
2. `[p]repo add Athena-Cogs https://github.com/arconyx/Athena-Cogs`
3. `[p]cog install Athena-Cogs <cogname>`
4. `[p]load <cogname>`

### ChatterBot
Be aware that it currently only works with the ! command prefix (I haven't gotten around to fixing that), requires MongoDB to be running and records all messages sent (in channels it isn't set to ignore) to a MongoDB database. Also, the cog does not distinguish between servers - messages learnt in one server could be repeated in any server it is in.

### KankaView
####Initial Setup
For this to work you'll need an Personal Access Token for Kanka. You can get this on your profile page, but you will need to contact the dev for API permissions first.
1. `[p]kankaset token <Personal Access Token>`
2. `[p]reload kankaview`
3. `[p]kanka campaign <Campain ID>`

####Tips
Your most used command will likely be the search command. I recommend setting up an alias for this command. I use 'dnd' since I am using Kanka for my D&D campaign, and that is a command that my players will easily recognize.
1. `[p]load alias`
2. `[p]alias add dnd kanka search`

Whenever you add a large number of entities to the campaign, you can significantly reduce loading times for the bot by running the refresh command `[p]kanka refresh`