from redbot.core import commands, Config, checks
import discord
import aiohttp
from markdownify import markdownify as md
import logging
from asyncio import sleep

DEFAULT_SETTINGS = {"token": None, "language": "en", "hide_private": True}
REQUEST_PATH = "https://kanka.io/api/1.0/"
STORAGE_PATH = "https://kanka-user-assets.s3.eu-central-1.amazonaws.com/"
MSG_ENTITY_NOT_FOUND = "Entity not found."
CACHE = {}

# TODO: OAuth user tokens?


class Campaign:
    def __init__(self, json_data):
        self.id = json_data.get("id")
        self.name = json_data.get("name")
        self.locale = json_data.get("locale")

        missing_entry_message = "<p>This campaign doesn't have a description yet.</p>"
        raw_entry = (
            json_data.get("entry")
            if json_data.get("entry") is not None
            else missing_entry_message
        )
        self.entry = md(raw_entry, strip=["img"])

        self.image = (
            f"{STORAGE_PATH}{json_data.get('image')}"
            if json_data.get("image") is not None
            else ""
        )
        self.visibility = json_data.get("visibility")
        self.created_at = json_data.get("created_at")
        self.updated_at = json_data.get("updated_at")
        self.members = json_data.get("members")
        self.entity_type = "campaign"

    def link(self, lang="en", pretty=True):  # TODO: Improve language support?
        link = f"https://kanka.io/{lang}/campaign/{self.id}/campaign"
        return f"[{self.name}]({link})" if pretty else link

    def __repr__(self):
        return (
            f"{self.__class__.__name__}"
            f"({', '.join(f'{key}={value!r}' for key, value in self.__dict__.items())})"
        )


class DiceRoll:
    # Dice are annoyingly inconsistant and so get a class without Entity
    def __init__(self, campaign_id, json_data):
        self.campaign_id = campaign_id
        self.id = json_data.get("id")
        self.character_id = json_data.get("character_id")
        self.name = json_data.get("name")
        self.slug = json_data.get("slug")
        self.system = json_data.get("system")
        self.parameters = json_data.get("parameters")
        self.is_private = json_data.get("private")
        self.created_at = json_data.get("created_at")
        self.updated_at = json_data.get("updated_at")
        self.image = (
            f"{STORAGE_PATH}{json_data.get('image')}"
            if json_data.get("image") is not None
            else ""
        )
        self.tags = json_data.get("tags")


class Entity:
    def __init__(self, campaign_id, json_data):
        self.campaign_id = campaign_id
        self.created_at = json_data.get("created_at")
        self.created_by = json_data.get("created_by")
        self.entity_id = json_data.get("entity_id")

        missing_entry_message = "<p>This entity doesn't have a description yet.</p>"
        raw_entry = (
            json_data.get("entry_parsed")
            if json_data.get("entry_parsed") is not None
            else missing_entry_message
        )
        self.entry = md(raw_entry, strip=["img"])

        self.id = json_data.get("id")
        self.image = (
            f"{STORAGE_PATH}{json_data.get('image')}"
            if json_data.get("image") is not None
            else ""
        )
        self.is_private = json_data.get("is_private")
        self.name = json_data.get("name")
        self.tags = json_data.get("tags")
        self.created_at = json_data.get("created_at")
        self.updated_at = json_data.get("updated_at")
        self.type_ = json_data.get("type")

        self.files = {}
        if "entity_files" in json_data:
            for entity in json_data.get("entity_files"):
                if entity.get("visibility") == "all":
                    self.files[entity.get("name")] = entity.get("path")
        else:
            self.files = None

    def link(self, lang="en", pretty=True):  # TODO: Improve language support?
        link = (
            f"https://kanka.io/{lang}/campaign/"
            f"{self.campaign_id}/{self.entity_type}/{self.id}"
        )
        return f"[{self.name}]({link})" if pretty else link


class Character(Entity):
    def __init__(self, campaign_id, json_data):
        super().__init__(campaign_id, json_data)
        self.age = json_data.get("age")
        self.family_id = json_data.get("family_id")
        self.is_dead = json_data.get("is_dead")
        self.location_id = json_data.get("location_id")
        self.race_id = json_data.get("race_id")
        self.sex = json_data.get("sex")
        self.title = json_data.get("title")
        self.entity_type = "characters"


class Location(Entity):
    def __init__(self, campaign_id, json_data):
        super().__init__(campaign_id, json_data)
        self.parent_location_id = json_data.get("parent_location_id")
        self.map = json_data.get("map")
        if "https://kanka.io/images/defaults" in self.map:
            self.map = None
        self.entity_type = "locations"


class Event(Entity):
    def __init__(self, campaign_id, json_data):
        super().__init__(campaign_id, json_data)
        self.date = json_data.get("date")
        self.location_id = json_data.get("location_id")
        self.entity_type = "events"


class Family(Entity):
    def __init__(self, campaign_id, json_data):
        super().__init__(campaign_id, json_data)
        self.location_id = json_data.get("location_id")
        self.parent_family_id = json_data.get("family_id")
        self.entity_type = "families"


class Calendar(Entity):
    def __init__(self, campaign_id, json_data):
        super().__init__(campaign_id, json_data)
        self.date = json_data.get("date")
        if json_data.get("has_leap_year"):
            self.leap_year = {
                "exist": json_data.get("has_leap_year"),
                "amount": json_data.get("leap_year_amount"),
                "month": json_data.get("leap_year_month"),
                "offset": json_data.get("leap_year_offset"),
                "start": json_data.get("leap_year_start"),
            }
        else:
            self.leap_year = {"exist": False}
        self.months = json_data.get("months")
        self.parameters = json_data.get("parameters")
        self.seasons = json_data.get("seasons")
        self.suffix = json_data.get("suffix")
        self.weekdays = json_data.get("weekdays")
        self.years = json_data.get("years")
        self.entity_type = "calendars"

    def get_month_names(self):
        names = ""
        for month in self.months:
            names += (month["name"]) + ", "
        names = names.strip(", ")
        return names

    def get_weekdays(self):
        names = ""
        for day in self.weekdays:
            names += day + ", "
        names = names.strip(", ")
        return names

    def get_year_length(self):
        days = 0
        for month in self.months:
            days += month["length"]
        return days


class Item(Entity):
    def __init__(self, campaign_id, json_data):
        super().__init__(campaign_id, json_data)
        self.location_id = json_data.get("location_id")
        self.character_id = json_data.get("character_id")
        self.entity_type = "items"


class Journal(Entity):
    def __init__(self, campaign_id, json_data):
        super().__init__(campaign_id, json_data)
        self.date = json_data.get("date")
        self.character_id = json_data.get("character_id")
        self.entity_type = "journals"


class Organisation(Entity):
    def __init__(self, campaign_id, json_data):
        super().__init__(campaign_id, json_data)
        self.location_id = json_data.get("location_id")
        self.members = json_data.get("members")
        self.entity_type = "organisations"


class Quest(Entity):
    def __init__(self, campaign_id, json_data):
        super().__init__(campaign_id, json_data)
        self.character_id = json_data.get("character_id")
        self.characters = json_data.get("characters")
        self.is_completed = json_data.get("is_completed")
        self.elements = json_data.get("elements")
        self.parent_quest_id = json_data.get("quest_id")
        self.entity_type = "quests"


class Tag(Entity):
    def __init__(self, campaign_id, json_data):
        super().__init__(campaign_id, json_data)
        self.tag_id = json_data.get("tag_id")
        self.entity_type = "tags"


class Note(Entity):
    def __init__(self, campaign_id, json_data):
        super().__init__(campaign_id, json_data)
        # self.is_pinned = json_data.get('is_pinned')
        self.entity_type = "notes"


class Race(Entity):
    def __init__(self, campaign_id, json_data):
        super().__init__(campaign_id, json_data)
        self.parent_race_id = json_data.get("race_id")
        self.entity_type = "races"


class Ability(Entity):
    def __init__(self, campaign_id, json_data):
        super().__init__(campaign_id, json_data)
        self.parent_ability_id = json_data.get("ability_id")
        self.charges = json_data.get("charges")
        self.entity_type = "abilities"


class Creature(Entity):
    def __init__(self, campaign_id, json_data):
        super().__init__(campaign_id, json_data)
        self.parent_creature_id = json_data.get("creature_id")
        self.locations = json_data.get("locations")
        self.entity_type = "Creatures"


class KankaView(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=56456483622343233254868, force_registration=True
        )
        self.config.register_global(token=None)
        self.config.register_guild(hide_private=True, language="en", active=None)
        self.session = None
        self.log = logging.getLogger("red.Athena-Cogs.kankaview")
        self.log.setLevel("WARNING")
        if self.bot.get_cog("Dev"):
            self.log.setLevel("DEBUG")
            self.log.debug("KankaView running in debug mode.")

    async def _language(self, ctx):
        language = await self.config.guild(ctx.guild).language()
        return language

    async def _active(self, ctx):
        await self._set_headers()
        active = await self.config.guild(ctx.guild).active()
        if active is None:
            await ctx.send(
                "No active campaign set. This will cause errors. "
                "Please set an active campaign with the `[p]kanka "
                "campaign <id>` command."
            )
        return active

    async def _set_headers(self):
        token = await self.config.token()
        if token:
            headers = {}
            headers["accept"] = "application/json"
            headers["authorization"] = token
            self.headers = headers
        else:
            self.headers = None
        if self.session is not None:
            await self.session.close()
        self.session = aiohttp.ClientSession(headers=self.headers)

    async def _verify_response(self, r: aiohttp.ClientResponse, check_json=True):
        if r.status == 200:
            if check_json and "data" not in await r.json():
                self.log.debug(f"Data key not in reponse to query {r.url}")
                self.log.debug(f"Response is {await r.json()}")
                return False
            return True
        elif r.status == 404:
            self.log.debug(f"404 for url {r.url}")
            return False
        elif r.status == 429:
            self.log.warning("Exceeded Kanka's ratelimit")
            return False
        else:
            self.log.warning(
                f"Unable to complete request. Server returned status code {r.status}."
            )
            return False

    async def _get_campaigns_list(self):
        await self._set_headers()
        async with self.session.get(REQUEST_PATH + "campaigns") as r:
            if not await self._verify_response(r):
                return None
            j = await r.json()
            return [Campaign(campaign) for campaign in j["data"]]

    async def _get_campaign(self, id):
        await self._set_headers()
        async with self.session.get(
            "{base_url}campaigns/{id}".format(base_url=REQUEST_PATH, id=id)
        ) as r:
            if not await self._verify_response(r):
                return None
            j = await r.json()
            return Campaign(j["data"])

    async def _get_entity(
        self, campaign_id, entity_type, entity_id, related=False, cache=False
    ):
        # Move privacy checking into here?
        if related and cache:
            raise ValueError(
                "The related and cache parameters cannot both be"
                " true as the cache lacks this information."
            )
        elif related:
            entity_id = f"{entity_id}?related=1"
        elif cache:
            cached_entity = await self._check_cache(campaign_id, entity_type, entity_id)
            if cached_entity is not None:
                return cached_entity

        async with self.session.get(
            f"{REQUEST_PATH}campaigns/{campaign_id}/{entity_type}/{entity_id}"
        ) as r:
            if not await self._verify_response(r):
                return None
            j = await r.json()

            self.log.debug(
                f"Get returned from {r.url} with status code {r.status}."
                "Body follows."
            )
            self.log.debug(j)

            if entity_type == "locations":
                return Location(campaign_id, j["data"])
            elif entity_type == "characters":
                return Character(campaign_id, j["data"])
            elif entity_type == "organisations":
                return Organisation(campaign_id, j["data"])
            elif entity_type == "items":
                return Item(campaign_id, j["data"])
            elif entity_type == "families":
                return Family(campaign_id, j["data"])
            elif entity_type == "quests":
                return Quest(campaign_id, j["data"])
            elif entity_type == "events":
                return Event(campaign_id, j["data"])
            elif entity_type == "notes":
                return Note(campaign_id, j["data"])
            elif entity_type == "calendars":
                return Calendar(campaign_id, j["data"])
            elif entity_type == "tags":
                return Tag(campaign_id, j["data"])
            elif entity_type == "journals":
                return Journal(campaign_id, j["data"])
            elif entity_type == "races":
                return Race(campaign_id, j["data"])
            elif entity_type == "abilities":
                return Ability(campaign_id, j["data"])
            elif entity_type == "creatures":
                return Creature(campaign_id, j["data"])
            else:
                self.log.debug(f"Invalid entity type for request {r.url} in return {j}")
                return None

    async def _get_diceroll(self, campaign_id, diceroll_id):
        # TODO: I think dice rolls are broken right now. Report bug.
        # TODO: Search by name
        async with self.session.get(
            f"{REQUEST_PATH}campaigns/{campaign_id}/dice_rolls/{diceroll_id}"
        ) as r:
            j = await r.json()
            return DiceRoll(campaign_id, j["data"])

    async def _cache_entities(self, campaign_id):
        # TODO: LastSync, expiry, update
        await self._cache_entity_by_type(campaign_id, "characters")
        await self._cache_entity_by_type(campaign_id, "locations")
        await self._cache_entity_by_type(campaign_id, "items")
        await self._cache_entity_by_type(campaign_id, "organisations")
        await self._cache_entity_by_type(campaign_id, "families")
        await self._cache_entity_by_type(campaign_id, "quests")
        await self._cache_entity_by_type(campaign_id, "notes")
        await self._cache_entity_by_type(campaign_id, "events")
        await self._cache_entity_by_type(campaign_id, "calendars")
        await self._cache_entity_by_type(campaign_id, "journals")
        await self._cache_entity_by_type(campaign_id, "tags")
        await self._cache_entity_by_type(campaign_id, "races")
        await self._cache_entity_by_type(campaign_id, "abilities")
        await self._cache_entity_by_type(campaign_id, "creatures")

    async def _cache_entity_by_type(self, campaign_id, entity_type: str):
        # API will only load 15-100 entities at a time.
        # Increment the page and load more if needed
        done = False
        page = 1

        if entity_type not in CACHE:
            CACHE[entity_type] = {}

        while not done:
            async with self.session.get(
                "{base_url}campaigns/"
                "{campaign_id}"
                "/{entity_type}"
                "?page={page}".format(
                    base_url=REQUEST_PATH,
                    campaign_id=campaign_id,
                    entity_type=entity_type,
                    page=page,
                )
            ) as r:
                if r.status == 429:
                    self.log.info("Exceeded Kanka's ratelimit. Sleeping.")
                    await sleep(30)
                    continue
                elif not await self._verify_response(r):
                    self.log.warning("Error while caching, aborting.")
                    return

                j = await r.json()

                # Use meta element page count instead?
                if len(j["data"]) == 0:
                    done = True
                else:
                    for i in range(len(j["data"])):
                        entity = Entity(campaign_id, j["data"][i])
                        entity.entity_type = entity_type
                        CACHE[entity_type][entity.id] = entity
                    page += 1

            await sleep(2)

    async def _parse_entry(self, ctx, parent):
        # get the entity's entry
        entry = parent.entry

        # Discord limits the embed to 2048 characters,
        # so lets save some work by cutting the length down to size
        # at the end, we will create a "Read More" link to pretty things up.
        if len(entry) > 2047:
            entry = entry[:2047]

        url = "https://kanka.io/{lang}/campaign/".format(lang=await self._language(ctx))
        entry = entry.replace("https://kanka.io/campaign/", url)

        # Entry length limit due to Discord embed rules
        if len(entry) > 1900:
            entry = entry[:1900] + "... [Read more.]({link})".format(
                link=parent.link(await self._language(ctx), pretty=False)
            )

        return entry

    async def _check_cache(self, campaign_id, entity_type, entity_id):
        # check cache for ID of entity.
        if entity_type not in CACHE or entity_id not in CACHE[entity_type]:
            # if the cache has not been loaded, or we are missing this ID,
            # try to reload the IDs
            await self._cache_entity_by_type(campaign_id, entity_type)
            if entity_type not in CACHE or entity_id not in CACHE[entity_type]:
                # if there is still a problem, give up
                return None
        # the ID has been loaded
        return CACHE[entity_type][entity_id]

    async def _search(self, cmpgn_id, query, entity_type=None):
        async with self.session.get(
            f"{REQUEST_PATH}campaigns/{cmpgn_id}/search/{query}"
        ) as r:
            if not await self._verify_response(r):
                return None

            j = await r.json()
            self.log.debug(
                f"Get returned from {r.url} with status code {r.status}."
                "Body follows."
            )
            self.log.debug(j)

            # if they've specified a type, look for it
            if entity_type and j.get("data"):
                for result in j.get("data"):
                    if result.get("type") == entity_type:
                        return result
                # if the loop ends with no matches the search couldn't find it
                return None
            elif j.get("data"):  # if not just blindly grab the first result
                return j["data"][0]
            elif "data" in j:  # if the search results are empty report no match
                return None

    async def _check_private(self, guild, entity):
        return entity.is_private and await self.config.guild(guild).hide_private()

    async def _process_display_input(self, ctx, input, entity_type, alert=True):
        try:
            id = int(input)
            return id
        except ValueError:
            entity = await self._search(await self._active(ctx), input, entity_type)
            if entity is not None:
                return entity["id"]
            else:
                if alert:
                    await ctx.send(MSG_ENTITY_NOT_FOUND)
                return None

    async def _display_entity(self, ctx, entity: Entity, alert=True):
        """Generate basic embed for any entity type"""
        # TODO: Attributes and relations
        if entity is None:
            await ctx.send(MSG_ENTITY_NOT_FOUND)
            return None
        elif await self._check_private(ctx.guild, entity):
            if alert:
                await ctx.send(MSG_ENTITY_NOT_FOUND)
            return None

        lang = await self._language(ctx)

        em = discord.Embed(
            title=f"{entity.name} :lock:" if entity.is_private else entity.name,
            description=await self._parse_entry(ctx, entity),
            url=entity.link(lang=lang, pretty=False),
            colour=discord.Color.blue(),
        )
        em.set_image(url=entity.image)
        em.add_field(name="Type", value=entity.type_)

        if entity.files:
            value = ""
            for file_name in entity.files:
                value += f"[{file_name}]({entity.files[file_name]}), "
            em.add_field(name="Files", value=value[0 : len(value) - 2])

        if entity.tags:
            tags = []
            for tag_id in entity.tags:
                tag = await self._get_entity(
                    entity.campaign_id, "tags", tag_id, cache=True
                )
                if not await self._check_private(ctx.guild, tag):
                    tags.append(tag.link(lang))
            if tags:  # Hide tag field when all are private
                em.add_field(name="Tags", value=", ".join(tags))

        return em

    async def _send(self, ctx, em):
        # Strip out empty fields for tidiness
        i = 0
        while i < len(em.fields):
            field = em.fields[i]
            if field.value == "None":
                em.remove_field(i)
            else:
                i += 1
        await ctx.send(embed=em)

    @commands.group(name="kanka")
    async def kanka(self, ctx):
        """Commands for interacting with Kanka campaigns. Most subcommands will
        accept an entity name or ID for the second parameter."""

    @kanka.command(name="campaigns")
    async def list_campaigns(self, ctx):
        """Lists campaigns the bot has access to."""
        campaigns = await self._get_campaigns_list()

        if not campaigns:
            await ctx.send("Unable to fetch campaigns. Check your API token is valid.")
            return

        em = discord.Embed(
            title="Campaigns List",
            description="{} campaigns found".format(len(campaigns)),
            colour=discord.Color.blue(),
        )
        # This only works with up to 25 campaigns
        # Change to use link class method?
        for campaign in campaigns:
            em.add_field(
                name=campaign.name,
                value="https://kanka.io/{lang}/campaign/{id}".format(
                    lang=await self._language(ctx), id=campaign.id
                ),
            )
        await ctx.send(embed=em)

    @kanka.command(name="campaign")
    async def display_campaign(self, ctx, id: int):
        """Display selected campaign and set campaign used for other
        commands."""
        # TODO: Add alias and name support
        campaign = await self._get_campaign(id)
        em = discord.Embed(
            title=campaign.name,
            description=await self._parse_entry(ctx, campaign),
            url="https://kanka.io/{lang}/campaign/{id}".format(
                lang=await self._language(ctx), id=campaign.id
            ),
            colour=discord.Color.blue(),
        )
        em.set_thumbnail(url=campaign.image)
        em.add_field(name="Owner:", value=campaign.members[0]["user"]["name"])
        em.add_field(name="Visibility", value=campaign.visibility)
        em.add_field(name="Locale", value=campaign.locale)
        em.add_field(
            name="Created At", value=campaign.created_at[:-11].replace("T", " ")
        )
        em.add_field(
            name="Updated At", value=campaign.updated_at[:-11].replace("T", " ")
        )
        await self.config.guild(ctx.guild).active.set(id)
        await ctx.send("Active campaign set.", embed=em)

        await ctx.send("Loading Entity info...")
        CACHE.clear()
        await self._cache_entities(id)
        length = 0
        for value in CACHE.values():
            length += len(value)
        await ctx.send(str(length) + " Entities loaded.")

    @kanka.command(name="character")
    async def display_character(self, ctx, input, alert=True):
        """Display selected character by name or ID."""
        id = await self._process_display_input(ctx, input, "character", alert)
        if id is None:
            return False

        char = await self._get_entity(
            await self._active(ctx), "characters", id, related=True
        )

        em = await self._display_entity(ctx, char, alert)
        if em is None:
            return False

        lang = await self._language(ctx)
        cmpgn_id = char.campaign_id

        em.add_field(name="Title", value=char.title)
        em.add_field(name="Age", value=char.age)
        em.add_field(name="Gender", value=char.sex)

        if char.is_dead:
            em.add_field(name="Status", value="Dead")
        else:
            em.add_field(name="Status", value="Alive")

        if char.race_id:
            race = await self._get_entity(cmpgn_id, "races", char.race_id)
            if not await self._check_private(ctx.guild, race):
                em.add_field(name="Race", value=race.link(lang))

        if char.location_id is not None:
            location = await self._get_entity(
                cmpgn_id, "locations", char.location_id, cache=True
            )
            if not await self._check_private(ctx.guild, location):
                em.add_field(name="Location", value=location.link(lang))

        if char.family_id:
            family = await self._get_entity(
                cmpgn_id, "families", char.family_id, cache=True
            )
            if not await self._check_private(ctx.guild, family):
                em.add_field(name="Family", value=family.link(lang))

        await self._send(ctx, em)
        return True

    @kanka.command(name="location")
    async def display_location(self, ctx, input, alert=True):
        """Display selected location by name or ID."""
        id = await self._process_display_input(ctx, input, "location", alert)
        if id is None:
            return False

        location = await self._get_entity(
            await self._active(ctx), "locations", id, True
        )

        em = await self._display_entity(ctx, location, alert)
        if em is None:
            return False

        lang = await self._language(ctx)
        cmpgn_id = location.campaign_id

        # TODO: Add support for new map entity then remove support for old
        if location.map is not None:  # Old style map only
            em.add_field(
                name="Map",
                value="[View Map]({location_link}/map)".format(
                    location_link=location.link(lang, False)
                ),
            )

        if location.parent_location_id is not None:
            parent = await self._get_entity(
                cmpgn_id, "locations", location.parent_location_id, cache=True
            )
            em.add_field(name="Parent Location", value=parent.link(lang))

        await ctx.send(embed=em)
        return True

    @kanka.command(name="event")
    async def display_event(self, ctx, input, alert=True):
        """Display selected event by name or ID."""
        id = await self._process_display_input(ctx, input, "event", alert)
        if id is None:
            return False

        event = await self._get_entity(await self._active(ctx), "events", id)

        em = await self._display_entity(ctx, event, alert)
        if em is None:
            return False

        lang = await self._language(ctx)
        cmpgn_id = event.campaign_id

        em.add_field(name="Date", value=event.date)

        if event.location_id is not None:
            location = await self._get_entity(
                cmpgn_id, "locations", event.location_id, cache=True
            )
            em.add_field(name="Location", value=location.link(lang))

        await self._send(ctx, em)
        return True

    @kanka.command(name="family")
    async def display_family(self, ctx, input, alert=True):
        """Display selected family by name or ID."""
        id = await self._process_display_input(ctx, input, "family", alert)
        if id is None:
            return False

        family = await self._get_entity(await self._active(ctx), "families", id)

        em = await self._display_entity(ctx, family, alert)
        if em is None:
            return False

        lang = await self._language(ctx)
        cmpgn_id = family.campaign_id

        if family.location_id is not None:
            location = await self._get_entity(
                cmpgn_id, "locations", family.location_id, cache=True
            )
            em.add_field(name="Location", value=location.link(lang))

        if family.parent_family_id is not None:
            parent = await self._get_entity(
                cmpgn_id, "families", family.parent_family_id, cache=True
            )
            em.add_field(name="Parent Family", value=parent.link(lang))

        await self._send(ctx, em)
        return True

    @kanka.command(name="calendar")
    async def display_calendar(self, ctx, input, alert=True):
        """Display selected calendar by name or ID."""
        id = await self._process_display_input(ctx, input, "calendar", alert)
        if id is None:
            return False

        calendar = await self._get_entity(await self._active(ctx), "calendars", id)

        em = await self._display_entity(ctx, calendar, alert)
        if em is None:
            return False

        # TODO: fix these fields. Concatenation error None type.
        # Probably an issue in the class JSON format
        em.add_field(name="Date", value=calendar.date + " " + calendar.suffix)
        em.add_field(name="Months", value=calendar.get_month_names())
        em.add_field(name="Length", value=str(calendar.get_year_length()))
        em.add_field(name="Days", value=calendar.get_weekdays())

        await self._send(ctx, em)
        return True

    @kanka.command(name="diceroll")
    async def display_diceroll(self, ctx, diceroll_id, alert=True):
        """Display selected dice roll. Deprecated."""
        # TODO: Attributes and relations
        # Deprecate? They are annoyingly inconsistant with the rest anyway.
        try:
            diceroll_id = int(diceroll_id)
        except ValueError:
            diceroll_id = await self._search(
                "diceroll", await self._active(ctx), diceroll_id
            )
            if diceroll_id == "NoResults":
                if alert:
                    await ctx.send(MSG_ENTITY_NOT_FOUND)
                return False
        diceroll = await self._get_diceroll(await self._active(ctx), diceroll_id)
        if not await self._check_private(ctx.guild, diceroll):
            em = discord.Embed(
                title=diceroll.name,
                description=diceroll.parameters,
                url="https://kanka.io/{lang}/campaign/"
                "{cmpgn_id}"
                "/dice_rolls/"
                "{diceroll_id}".format(
                    lang=await self._language(ctx),
                    cmpgn_id=await self._active(ctx),
                    diceroll_id=diceroll_id,
                ),
                colour=discord.Color.blue(),
            )
            em.set_thumbnail(url=diceroll.image)
            await ctx.send(embed=em)
        else:
            await ctx.send(MSG_ENTITY_NOT_FOUND)

    @kanka.command(name="item")
    async def display_item(self, ctx, input, alert=True):
        """Display selected item by name or ID."""
        id = await self._process_display_input(ctx, input, "item", alert)
        if id is None:
            return False

        item = await self._get_entity(await self._active(ctx), "items", id)

        em = await self._display_entity(ctx, item, alert)
        if em is None:
            return False

        lang = await self._language(ctx)
        cmpgn_id = item.campaign_id

        if item.character_id is not None:
            owner = await self._get_entity(
                cmpgn_id, "characters", item.character_id, cache=True
            )
            em.add_field(name="Owner", value=owner.link(lang))

        if item.location_id is not None:
            location = await self._get_entity(
                cmpgn_id, "locations", item.location_id, cache=True
            )
            em.add_field(name="Location", value=location.link(lang))

        await self._send(ctx, em)
        return True

    @kanka.command(name="journal")
    async def display_journal(self, ctx, input, alert=True):
        """Display selected journal by name or ID."""
        id = await self._process_display_input(ctx, input, "journal", alert)
        if id is None:
            return False

        journal = await self._get_entity(await self._active(ctx), "journals", id)

        em = await self._display_entity(ctx, journal, alert)
        if em is None:
            return False

        lang = await self._language(ctx)
        cmpgn_id = journal.campaign_id

        if journal.date is not None:
            em.add_field(name="Date", value=journal.date)

        if journal.character_id is not None:
            author = await self._get_entity(
                cmpgn_id, "journals", journal.character_id, cache=True
            )
            em.add_field(name="Author", value=author.link(lang))

        await self._send(ctx, em)
        return True

    @kanka.command(name="organisation")
    async def display_organisation(self, ctx, input, alert=True):
        """Display selected organisation by name or ID."""
        # TODO: Get and list members
        id = await self._process_display_input(ctx, input, "organisation", alert)
        if id is None:
            return False

        organisation = await self._get_entity(
            await self._active(ctx), "organisations", id
        )

        em = await self._display_entity(ctx, organisation, alert)
        if em is None:
            return False

        lang = await self._language(ctx)
        cmpgn_id = organisation.campaign_id

        if organisation.members:
            members = []
            for m in organisation.members:
                member = await self._get_entity(
                    cmpgn_id, "characters", m.get("character_id"), cache=True
                )
                if not await self._check_private(ctx.guild, member):
                    members.append(member.link(lang))
            if members:  # Hide field when all members are private
                em.add_field(name="Members", value=", ".join(members))
                # The members information in organisation.members
                # includes an is_private field - consult that?

        if organisation.location_id is not None:
            location = await self._get_entity(
                cmpgn_id, "locations", organisation.location_id, cache=True
            )
            em.add_field(name="Location", value=location.link(lang))

        await self._send(ctx, em)
        return True

    @kanka.command(name="quest")
    async def display_quest(self, ctx, input, alert=True):
        """Display selected quest by name or ID."""
        # TODO: Get and list members
        id = await self._process_display_input(ctx, input, "quest", alert)
        if id is None:
            return False

        quest: Quest = await self._get_entity(await self._active(ctx), "quests", id)

        em = await self._display_entity(ctx, quest, alert)
        if em is None:
            return False

        lang = await self._language(ctx)
        cmpgn_id = quest.campaign_id

        if quest.character_id is not None:
            instigator = await self._get_entity(
                cmpgn_id, "characters", quest.character_id, cache=True
            )
            em.add_field(name="Instigator", value=instigator.link(lang))

        em.add_field(name="Completed", value=quest.is_completed)
        em.add_field(name="Characters", value=quest.characters)

        if quest.parent_quest_id is not None:
            parent = await self._get_entity(
                cmpgn_id, "quests", quest.parent_quest_id, cache=True
            )
            em.add_field(name="Parent Quest", value=parent.link(lang))

        if quest.elements:
            elements = []
            for el in quest.elements:
                name = None
                url = None

                if el.get("entity_id"):
                    async with self.session.get(
                        f"{REQUEST_PATH}campaigns/{cmpgn_id}/entities/{el['entity_id']}"
                    ) as r:
                        if not await self._verify_response(r):
                            continue
                        j = await r.json()
                        j = j["data"]

                        self.log.debug(f"Get from {r.url} with status {r.status}")
                        self.log.debug(j)

                        name = j["name"]
                        url = j["child"]["urls"]["view"]
                if el.get("name"):
                    name = el["name"]

                link = f"[{name}]({url})" if url else name

                elements.append(link)

            if elements:
                em.add_field(name="Elements", value=", ".join(elements))

        await self._send(ctx, em)
        return True

    @kanka.command(name="tag")
    async def display_tag(self, ctx, input, alert=True):
        """Display selected tag by name or ID."""
        # TODO: Get and list children and subcategories
        id = await self._process_display_input(ctx, input, "tag", alert)
        if id is None:
            return False

        tag = await self._get_entity(await self._active(ctx), "tags", id)

        em = await self._display_entity(ctx, tag, alert)
        if em is None:
            return False

        lang = await self._language(ctx)
        cmpgn_id = tag.campaign_id

        if tag.tag_id is not None:
            parent = await self._get_entity(cmpgn_id, "tags", tag.tag_id, cache=True)
            em.add_field(name="Parent Tag", value=parent.link(lang))

        await self._send(ctx, em)
        return True

    @kanka.command(name="note")
    async def display_note(self, ctx, input, alert=True):
        """Display selected note by name or ID."""
        id = await self._process_display_input(ctx, input, "note", alert)
        if id is None:
            return False

        note = await self._get_entity(await self._active(ctx), "notes", id)

        em = await self._display_entity(ctx, note, alert)
        if em is None:
            return False

        await self._send(ctx, em)
        return True

    @kanka.command(name="race")
    async def display_race(self, ctx, input, alert=True):
        """Display selected race by name or ID."""
        id = await self._process_display_input(ctx, input, "race", alert)
        if id is None:
            return False

        race = await self._get_entity(await self._active(ctx), "races", id)

        em = await self._display_entity(ctx, race, alert)
        if em is None:
            return False

        lang = await self._language(ctx)
        cmpgn_id = race.campaign_id

        if race.parent_race_id is not None:
            parent = await self._get_entity(
                cmpgn_id, "races", race.parent_race_id, cache=True
            )
            em.add_field(name="Parent Race", value=parent.link(lang))

        await self._send(ctx, em)
        return True

    @kanka.command(name="ability")
    async def display_ability(self, ctx, input, alert=True):
        """Display selected ability by name or ID."""
        id = await self._process_display_input(ctx, input, "ability", alert)
        if id is None:
            return False

        ability = await self._get_entity(await self._active(ctx), "abilities", id)

        em = await self._display_entity(ctx, ability, alert)
        if em is None:
            return False

        lang = await self._language(ctx)
        cmpgn_id = ability.campaign_id

        if ability.parent_ability_id is not None:
            parent = await self._get_entity(
                cmpgn_id, "abilities", ability.parent_ability_id, cache=True
            )
            em.add_field(name="Parent Ability", value=parent.link(lang))

        if ability.charges is not None:
            em.add_field(name="Charges", value=ability.charges)

        await self._send(ctx, em)
        return True

    @kanka.command(name="creature")
    async def display_creature(self, ctx, input, alert=True):
        """Display selected creature by name or ID."""
        id = await self._process_display_input(ctx, input, "creature", alert)
        if id is None:
            return False

        creature: Creature = await self._get_entity(
            await self._active(ctx), "creatures", id
        )

        em = await self._display_entity(ctx, creature, alert)
        if em is None:
            return False

        lang = await self._language(ctx)
        cmpgn_id = creature.campaign_id

        if creature.parent_creature_id is not None:
            parent = await self._get_entity(
                cmpgn_id, "creatures", creature.parent_creature_id, cache=True
            )
            em.add_field(name="Parent Creature", value=parent.link(lang))

        if creature.locations:
            locations = []
            for loc_id in creature.locations:
                loc: Location = await self._get_entity(
                    creature.campaign_id, "locations", loc_id, cache=True
                )
                if not await self._check_private(ctx.guild, loc):
                    locations.append(loc.link(lang))
            if locations:
                em.add_field(name="Locations", value=", ".join(locations))

        await self._send(ctx, em)
        return True

    @kanka.command(name="search")
    async def display_search(self, ctx, query):
        """Display selected Entity."""

        entity = await self._search(await self._active(ctx), query)

        if entity is None:
            await ctx.send(MSG_ENTITY_NOT_FOUND)
            return False

        entity_type = entity["type"]
        id = entity["id"]

        # We have to get the entity again
        # because the search endpoint gives truncated data
        if entity_type == "character":
            await self.display_character(ctx, id)
            return
        elif entity_type == "location":
            await self.display_location(ctx, id)
            return
        elif entity_type == "organisation":
            await self.display_organisation(ctx, id)
            return
        elif entity_type == "family":
            await self.display_family(ctx, id)
            return
        elif entity_type == "calendar":
            await self.display_calendar(ctx, id)
            return
        elif entity_type == "race":
            await self.display_race(ctx, id)
            return
        elif entity_type == "quest":
            await self.display_quest(ctx, id)
            return
        elif entity_type == "journal":
            await self.display_journal(ctx, id)
            return
        elif entity_type == "item":
            await self.display_item(ctx, id)
            return
        elif entity_type == "event":
            await self.display_event(ctx, id)
            return
        elif entity_type == "note":
            await self.display_note(ctx, id)
            return
        elif entity_type == "tag":
            await self.display_tag(ctx, id)
            return
        elif entity_type == "ability":
            await self.display_ability(ctx, id)
            return
        elif entity_type == "creature":
            await self.display_creature(ctx, id)
        else:
            await ctx.send(MSG_ENTITY_NOT_FOUND)
            return

    @kanka.command(name="refresh")
    async def load_cache(self, ctx):
        """Cache basic entity information. May help reduce loading times."""
        await ctx.send("Loading Entity info...")
        await self._cache_entities(await self._active(ctx))
        length = 0
        for value in CACHE.values():
            length += len(value)
        await ctx.send(str(length) + " Entities loaded.")

    @commands.group(name="kankaset")
    @checks.admin_or_permissions(manage_guild=True)
    async def kankaset(self, ctx):
        """Configuration commands for KankaView"""

    @kankaset.command(name="token")
    async def set_token(self, ctx, token: str):
        """Set API token ('Personal Access Token'). Do not include 'Bearer '.
        Be aware that this token is stored in plaintext by the bot."""
        if token[:7] != "Bearer ":
            token = "Bearer " + token
        await self.config.token.set(token)
        await self._set_headers()
        await ctx.send("API token set.")

    @kankaset.command(name="language")
    async def set_language(self, ctx, language: str):
        """Set language used in links. Valid language codes are en, de, en-US,
        es, fr, pt-BR"""
        LANGUAGES = ["en", "de", "en-US", "es", "fr", "pt-BR"]
        if language in LANGUAGES:
            await self.config.guild(ctx.guild).language.set(language)
            await ctx.send(f"Language set to {language}")
        else:
            await ctx.send_help()

    @kankaset.command(name="toggleprivate")
    async def hide_private(self, ctx):
        """Toggle if private entities are hidden."""
        hide_private = await self.config.guild(ctx.guild).hide_private()
        if hide_private:
            await self.config.guild(ctx.guild).hide_private.set(False)
            await ctx.send("Now showing private entities.")
        else:
            await self.config.guild(ctx.guild).hide_private.set(True)
            await ctx.send("Now hiding private entities.")

    @kankaset.command(name="reset")
    async def restore_default_settings(self, ctx):
        """Return to default settings."""
        # TODO: Add confirmation before deletion for safety
        await self.config.guild(ctx.guild).clear()
        CACHE.clear()
        await ctx.send("Server specific settings reset to default.")

    @kankaset.command(name="forceheaders")
    async def force_headers(self, ctx):
        """Forces header creation, resolves some issues."""
        await self._set_headers()
        await ctx.send("Set headers.")
