# Athena-Cogs
Random cogs I have created for [Red-DiscordBot](https://github.com/Cog-Creators/Red-DiscordBot).

## Working Cogs
These are at a point where you can actually use them.
* inspire - Generate inspiration quotes using [InspiroBot](http://inspirobot.me).
* kankaview - Access your [Kanka](https://kanka.io) campaigns from Discord.
* quake - Pulls information on recent earthquakes from [GeoNet](https://www.geonet.org.nz).

## Installation Notes
### General
I haven't gotten around to applying for cogs.red listing yet so you won't be able to install them through there. Instead you'll want to run these two commands (`[p]` should be replaced with the bot's command prefix):
1. `[p]load downloader`
2. `[p]repo add Athena-Cogs https://github.com/arconyx/Athena-Cogs`
3. `[p]cog install Athena-Cogs <cogname>`
4. `[p]load <cogname>`

### KankaView
**Initial Setup**

For this to work you'll need an Personal Access Token for Kanka. You can get this on your profile page - https://kanka.io/en/settings/api
1. `[p]kankaset token <Personal Access Token>`
2. `[p]reload kankaview`
3. `[p]kanka campaign <Campain ID>`
The bot will be able to view same entities as the account that owns the token so you may wish to use an alternate account with less permissions if you are a campaign admin.

**Tips**

Your most used command will likely be the search command. I recommend setting up an alias for this command. I use 'dnd' since I am using Kanka for my D&D campaign, and that is a command that my players will easily recognize.
1. `[p]load alias`
2. `[p]alias add dnd kanka search`

Whenever you add a large number of entities to the campaign, you can significantly reduce loading times for the bot by running the refresh command `[p]kanka refresh`

Private entities are hidden by default. Bot owners can change this using the `[p]kankaset toggleprivate` command.