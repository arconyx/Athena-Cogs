from redbot.core import commands, Config, checks
import discord
import aiohttp
import tomd
import json
import re

DEFAULT_SETTINGS = {'token': None, 'language': 'en', 'hide_private': True}
REQUEST_PATH = 'https://kanka.io/api/1.0/'
STORAGE_PATH = 'https://kanka-user-assets.s3.eu-central-1.amazonaws.com/'
MSG_ENTITY_NOT_FOUND = 'Entity not found.'
ID_MAP = {}


# TODO: OAuth user tokens?


class Campaign:
    def __init__(self, json_data):
        self.id = json_data['id']
        self.name = json_data['name']
        self.locale = json_data['locale']
        self.entry = tomd.convert(json_data['entry'])
        if json_data['image']:
            self.image = STORAGE_PATH + json_data['image']
        else:
            self.image = ''
        self.visibility = json_data['visibility']
        self.created_at = json_data['created_at']
        self.updated_at = json_data['updated_at']
        self.members = json_data['members']
        self.type = 'campaign'


class DiceRoll:
    # Dice are annoyingly inconsistant and so get a class without Entity
    def __init__(self, campaign_id, json_data):
        self.campaign_id = campaign_id
        self.id = json_data['id']
        self.character_id = json_data['character_id']
        self.name = json_data['name']
        self.slug = json_data['slug']
        self.system = json_data['system']
        self.parameters = json_data['parameters']
        self.is_private = json_data['private']
        self.created = {'at': json_data['created_at']}
        self.updated = {'at': json_data['created_at']}
        if json_data['image_full']:
            self.image = STORAGE_PATH + json_data['image_full']
        else:
            self.image = ''
        self.tags = json_data['tags']


class Entity:
    def __init__(self, campaign_id, json_data):
        self.campaign_id = campaign_id
        self.created = {'at': json_data['created_at'],
                        'by': json_data['created_by']}
        self.entity_id = json_data['entity_id']
        if json_data['entry'] is None:
            json_data['entry'] = ('<p>This entity doesn\'t have an description'
                                  + ' yet.</p>')
        self.entry = tomd.convert(json_data['entry'])
        self.id = json_data['id']
        if json_data['image_full']:
            self.image = STORAGE_PATH + json_data['image_full']
        else:
            self.image = ''
        self.is_private = json_data['is_private']
        self.name = json_data['name']
        self.tags = json_data['tags']
        self.updated = {'at': json_data['updated_at'],
                        'by': json_data['updated_by']}
        self.kind = json_data['type']


class Character(Entity):
    def __init__(self, campaign_id, json_data):
        super(Character, self).__init__(campaign_id, json_data)
        self.age = json_data['age']
        self.family_id = json_data['family_id']
        self.is_dead = json_data['is_dead']
        self.location_id = json_data['location_id']
        # TODO: Add race support back
        # self.race = json_data['race']
        self.sex = json_data['sex']
        self.title = json_data['title']
        self.files = {}
        if json_data['entity_files']['data']:
            for i in range(len(json_data['entity_files']['data'])):
                # TODO: include private files if hide_private is false
                if json_data['entity_files']['data'][i]['visibility'] == 'all':
                    self.files[json_data['entity_files']['data'][i]['name']] = json_data['entity_files']['data'][i]['path']
        else:
            self.file = None
        self.type = 'characters'


class Location(Entity):
    def __init__(self, campaign_id, json_data):
        super(Location, self).__init__(campaign_id, json_data)
        self.parent_location_id = json_data['parent_location_id']
        self.map = json_data['map']
        self.type = 'locations'


class Event(Entity):
    def __init__(self, campaign_id, json_data):
        super(Event, self).__init__(campaign_id, json_data)
        self.date = json_data['date']
        self.location_id = json_data['location_id']
        self.type = 'events'


class Family(Entity):
    def __init__(self, campaign_id, json_data):
        super(Family, self).__init__(campaign_id, json_data)
        self.location_id = json_data['location_id']
        self.type = 'families'


class Calendar(Entity):
    def __init__(self, campaign_id, json_data):
        super(Calendar, self).__init__(campaign_id, json_data)
        self.date = json_data['date']
        if json_data['has_leap_year']:
            self.leap_year = {'exist': json_data['has_leap_year'],
                              'amount': json_data['leap_year_amount'],
                              'month': json_data['leap_year_month'],
                              'offset': json_data['leap_year_offset'],
                              'start': json_data['leap_year_start']
                              }
        else:
            self.leap_year = {'exist': False}
        self.months = json_data['months']
        self.parameters = json_data['parameters']
        self.seasons = json_data['seasons']
        self.suffix = json_data['suffix']
        self.weekdays = json_data['weekdays']
        self.years = json_data['years']
        self.type = 'calendars'

    def get_month_names(self):
        names = ''
        for month in self.months:
            names += ((month['name']) + ', ')
        names = names.strip(', ')
        return names

    def get_weekdays(self):
        names = ''
        for day in self.weekdays:
            names += (day + ', ')
        names = names.strip(', ')
        return names

    def get_year_length(self):
        days = 0
        for month in self.months:
            days += month['length']
        return days


class Item(Entity):
    def __init__(self, campaign_id, json_data):
        super(Item, self).__init__(campaign_id, json_data)
        self.location_id = json_data['location_id']
        self.character_id = json_data['character_id']
        self.type = 'items'


class Journal(Entity):
    def __init__(self, campaign_id, json_data):
        super(Journal, self).__init__(campaign_id, json_data)
        self.date = json_data['date']
        self.character_id = json_data['character_id']
        self.type = 'journals'


class Organisation(Entity):
    def __init__(self, campaign_id, json_data):
        super(Organisation, self).__init__(campaign_id, json_data)
        self.location_id = json_data['location_id']
        self.members = json_data['members']
        self.type = 'organisations'


class Quest(Entity):
    def __init__(self, campaign_id, json_data):
        super(Quest, self).__init__(campaign_id, json_data)
        self.character_id = json_data['character_id']
        self.characters = json_data['characters']
        self.is_completed = json_data['is_completed']
        self.locations = json_data['locations']
        self.parent_quest_id = json_data['quest_id']
        self.type = 'quests'


class Tag(Entity):
    def __init__(self, campaign_id, json_data):
        super(Tag, self).__init__(campaign_id, json_data)
        self.tag_id = json_data['tag_id']
        self.type = 'tags'


class Note(Entity):
    def __init__(self, campaign_id, json_data):
        super(Note, self).__init__(campaign_id, json_data)
        self.is_pinned = json_data['is_pinned']
        self.type = 'notes'


class Race(Entity):
    def __init__(self, campaign_id, json_data):
        super(Race, self).__init__(campaign_id, json_data)
        self.parent_race_id = json_data['race_id']
        self.type = 'races'


class KankaView(commands.Cog):
    def __init__(self):
        self.config = Config.get_conf(self, identifier=56456483622343233254868,
                                      force_registration=True)
        self.config.register_global(
            token=None
        )
        self.config.register_guild(
            hide_private=True,
            language='en',
            active=None
        )
        self.session = None

    async def _language(self, ctx):
        language = await self.config.guild(ctx.guild).language()
        return language

    async def _active(self, ctx):
        await self._set_headers()
        active = await self.config.guild(ctx.guild).active()
        if active is None:
            await ctx.send('No active campaign set. This will cause errors. '
                           'Please set an active campaign with the `[p]kanka '
                           'campaign <id>` command.')
        return active

    async def _set_headers(self):
        token = await self.config.token()
        if token:
            headers = {}
            headers['accept'] = 'application/json'
            headers['authorization'] = token
            self.headers = headers
        else:
            self.headers = None
        if self.session is not None:
            await self.session.close()
        self.session = aiohttp.ClientSession(headers=self.headers)

    async def _get_campaigns_list(self):
        await self._set_headers()
        async with self.session.get(REQUEST_PATH + 'campaigns') as r:
            j = await r.json()
            campaigns = []
            for campaign in j['data']:
                campaigns.append(Campaign(campaign))
            return campaigns

    async def _get_campaign(self, id):
        await self._set_headers()
        async with self.session.get('{base_url}campaigns/{id}'.format(
                base_url=REQUEST_PATH,
                id=id)
        ) as r:
            j = await r.json()
            return Campaign(j['data'])

    async def _get_entity(self, campaign_id, entity_type, entity_id):
        # to get related entities, add related=1 URL parameter
        # currently only being used for characters
        if entity_type == 'characters':
            entity_id = str(entity_id) + '?related=1'

        async with self.session.get('{base_url}campaigns/'
                                    '{campaign_id}'
                                    '/{entity_type}/'
                                    '{entity_id}'.format(
            base_url=REQUEST_PATH,
            campaign_id=campaign_id,
            entity_type=entity_type,
            entity_id=entity_id)
        ) as r:
            j = await r.json()
            if entity_type == 'locations':
                return Location(campaign_id, j['data'])
            elif entity_type == 'characters':
                return Character(campaign_id, j['data'])
            elif entity_type == 'organisations':
                return Organisation(campaign_id, j['data'])
            elif entity_type == 'items':
                return Item(campaign_id, j['data'])
            elif entity_type == 'families':
                return Family(campaign_id, j['data'])
            elif entity_type == 'quests':
                return Quest(campaign_id, j['data'])
            elif entity_type == 'events':
                return Event(campaign_id, j['data'])
            elif entity_type == 'notes':
                return Note(campaign_id, j['data'])
            elif entity_type == 'calendars':
                return Calendar(campaign_id, j['data'])
            elif entity_type == 'tags':
                return Tag(campaign_id, j['data'])
            elif entity_type == 'journals':
                return Journal(campaign_id, j['data'])
            else:
                return None

    async def _get_diceroll(self, campaign_id, diceroll_id):
        # TODO: I think dice rolls are broken right now. Report bug.
        # TODO: Search by name
        async with self.session.get('{base_url}campaigns/'
                                    '{campaign_id}'
                                    '/dice_rolls/'
                                    '{diceroll_id}'.format(
            base_url=REQUEST_PATH,
            campaign_id=campaign_id,
            diceroll_id=diceroll_id)
        ) as r:
            j = await r.json()
            return DiceRoll(campaign_id, j['data'])

    async def _load_entity_id_map(self, campaign_id):
        await self._load_entity_ids_by_type(campaign_id, 'characters')
        await self._load_entity_ids_by_type(campaign_id, 'locations')
        await self._load_entity_ids_by_type(campaign_id, 'items')
        await self._load_entity_ids_by_type(campaign_id, 'organisations')
        await self._load_entity_ids_by_type(campaign_id, 'families')
        await self._load_entity_ids_by_type(campaign_id, 'quests')
        await self._load_entity_ids_by_type(campaign_id, 'notes')
        await self._load_entity_ids_by_type(campaign_id, 'events')
        await self._load_entity_ids_by_type(campaign_id, 'calendars')
        await self._load_entity_ids_by_type(campaign_id, 'journals')
        await self._load_entity_ids_by_type(campaign_id, 'tags')

    async def _load_entity_ids_by_type(self, campaign_id, entity_type):
        # API will only load 15-100 entities at a time. Increment the page and load more if needed
        done = False
        page = 1
        while not done:
            async with self.session.get('{base_url}campaigns/'
                                        '{campaign_id}'
                                        '/{entity_type}'
                                        '?page={page}'.format(
                base_url=REQUEST_PATH,
                campaign_id=campaign_id,
                entity_type=entity_type,
                page=page)
            ) as r:
                j = await r.json()
                if len(j['data']) == 0:
                    done = True
                else:
                    for i in range(len(j['data'])):
                        entity = Entity(campaign_id, j['data'][i])
                        ID_MAP[entity.entity_id] = entity.id
                    page += 1

    async def _parse_entry(self, ctx, campaign_id, parent):
        # regex query to find mentions
        regex = re.compile('\[.*?\]')

        # get the entity's entry
        entry = parent.entry

        # Discord limits the embed to 2048 characters, so lets save some work by cutting the length down to size
        # at the end, we will create a "Read More" link to pretty things up.
        if len(entry) > 2047:
            entry = entry[:2047]

        # replace each mention with a hyperlink to the correct entity
        for mention in regex.findall(entry):
            # initialize entity name
            entity_name = ''

            # split the entity type and ID from the mention string
            delim = mention.find(':')
            if delim > 3:
                entity_type = mention[1:delim]
                end = mention.find('|')
                if end < 4:
                    end = len(mention) - 1
                else:
                    # we have an advanced mention here. Grab the name.
                    entity_name = mention[end+1:len(mention)-1]
                entity_id = mention[delim+1:end]

                # convert entity type to plural
                if entity_type == 'family':
                    entity_type = 'families'
                else:
                    entity_type += 's'

                # get the entity using its type and ID
                entity = await self._get_mention(campaign_id, entity_type, int(entity_id))

                # if we were able to retrieve the entity, build a hyperlink to replace the mention
                if entity is not None and not await self._check_private(ctx.guild, entity):
                    if not entity_name:
                        entity_name = entity.name
                    url = '[{name}](https://kanka.io/{lang}/campaign/{cmpgn_id}/{type}/{id})'.format(
                        name=entity_name,
                        lang=await self._language(ctx),
                        cmpgn_id=await self._active(ctx),
                        type=entity_type,
                        id=entity.id
                    )
                    # replace the mention string with the hyperlink
                    entry = entry.replace(mention, url)
                else:
                    # otherwise, use 'Unknown' to CYA
                    entry = entry.replace(mention, 'Unknown')

        # Entry length limit due to Discord embed rules
        if len(entry) > 1900:
            entry = entry[:1900] + '...' + '[ Read more.](https://kanka.io/{lang}/campaign/{cmpgn_id}/{type}/{id})'.format(
                    lang=await self._language(ctx),
                    cmpgn_id=await self._active(ctx),
                    type=parent.type,
                    id=parent.id)

        return entry

    async def _get_mention(self, campaign_id, entity_type, entity_id):
        # check ID map to avoid misses
        if not await self._check_map(campaign_id, entity_type, entity_id):
            return None
        else:
            return await self._get_entity(campaign_id, entity_type, ID_MAP[entity_id])

    async def _check_map(self, campaign_id, entity_type, entity_id):
        # check ID map to avoid misses
        if len(ID_MAP) == 0 or entity_id not in ID_MAP:
            # if the ID map has not been loaded, or we are missing this ID, try to reload the IDs
            await self._load_entity_ids_by_type(campaign_id, entity_type)
            if len(ID_MAP) == 0 or entity_id not in ID_MAP:
                # if there is still a problem, give up
                return False
        # the ID has been loaded
        return True

    async def _search(self, kind, cmpgn_id, query):
        # TODO: Remove kind requirement
        async with self.session.get(
                '{base_url}campaigns/{cmpgn_id}/search/{query}'.format(
                    base_url=REQUEST_PATH,
                    cmpgn_id=cmpgn_id,
                    query=query
                )
        ) as r:
            j = await r.json()
            for result in j['data']:
                if result['type'] == kind:
                    return result['id']
            # This should only get called if there are no results
            return 'NoResults'

    async def _check_private(self, guild, entity):
        if entity.is_private and await self.config.guild(guild).hide_private():
            return True
        else:
            return False

    @commands.group(name='kanka')
    async def kanka(self, ctx):
        """Commands for interacting with Kanka campaigns. Most subcommands will
        accept an entity name or ID for the second parameter."""

    @kanka.command(name='campaigns')
    async def list_campaigns(self, ctx):
        """Lists campaigns the bot has access to."""
        campaigns = await self._get_campaigns_list()
        em = discord.Embed(title='Campaigns List',
                           description='{} campaigns found'.format(
                               len(campaigns)),
                           colour=discord.Color.blue())
        # This only works with up to 25 campaigns
        for campaign in campaigns:
            em.add_field(name=campaign.name,
                         value='https://kanka.io/{lang}/campaign/{id}'.format(
                             lang=await self._language(ctx),
                             id=campaign.id
                         ))
        await ctx.send(embed=em)

    @kanka.command(name='campaign')
    async def display_campaign(self, ctx, id: int):
        """Display selected campaign and set campaign used for other
        commands."""
        # TODO: Add alias and name support
        campaign = await self._get_campaign(id)
        em = discord.Embed(title=campaign.name,
                           description=await self._parse_entry(ctx, id, campaign),
                           url='https://kanka.io/{lang}/campaign/{id}'.format(
                               lang=await self._language(ctx),
                               id=campaign.id),
                           colour=discord.Color.blue())
        em.set_thumbnail(url=campaign.image)
        em.add_field(name='Owner:', value=campaign.members[0]['user']['name'])
        em.add_field(name='Visibility', value=campaign.visibility)
        em.add_field(name='Locale', value=campaign.locale)
        em.add_field(name='Created At',
                     value=campaign.created_at[:-11].replace('T', ' '))
        em.add_field(name='Updated At',
                     value=campaign.updated_at[:-11].replace('T', ' '))
        await self.config.guild(ctx.guild).active.set(id)
        await ctx.send('Active campaign set.', embed=em)

        await ctx.send('Loading Entity info...')
        ID_MAP.clear()
        await self._load_entity_id_map(id)
        await ctx.send(str(len(ID_MAP)) + ' Entities loaded.')

    @kanka.command(name='character')
    async def display_character(self, ctx, character_id, alert=True):
        """Display selected character."""
        # TODO: Attributes and relations
        try:
            character_id = int(character_id)
        except ValueError:
            character_id = await self._search('character',
                                              await self._active(ctx),
                                              character_id)
            if character_id == 'NoResults':
                if alert:
                    await ctx.send(MSG_ENTITY_NOT_FOUND)
                return False
        char = await self._get_entity(await self._active(ctx), 'characters', character_id)
        if not await self._check_private(ctx.guild, char):
            em = discord.Embed(title=char.name,
                               description=await self._parse_entry(ctx, await self._active(ctx), char),
                               url='https://kanka.io/{lang}/campaign/'
                                   '{cmpgn_id}'
                                   '/characters/'
                                   '{character_id}'
                               .format(
                                   lang=await self._language(ctx),
                                   cmpgn_id=await self._active(ctx),
                                   character_id=character_id),
                               colour=discord.Color.blue())
            em.set_image(url=char.image)
            em.add_field(name='Title', value=char.title)
            em.add_field(name='Age', value=char.age)
            em.add_field(name='Type', value=char.kind)
            # em.add_field(name='Race', value=char.race) # TODO: Display race
            if char.is_dead:
                em.add_field(name='Status', value='Dead')
            else:
                em.add_field(name='Status', value='Alive')
            em.add_field(name='Gender', value=char.sex)
            if char.location_id is not None:
                em.add_field(name='Location', value='[View Location](https://kanka.io/{lang}/'
                                                    'campaign/'
                                                    '{cmpgn_id}'
                                                    '/locations/'
                                                    '{location_id})'
                             .format(
                    lang=await self._language(ctx),
                    cmpgn_id=await self._active(ctx),
                    location_id=char.location_id))
            if char.files:
                value = ''
                for file_name in char.files:
                    value += '[{name}]({path}), '.format(name=file_name, path=char.files[file_name])
                em.add_field(name='Files', value=value[0:len(value) - 2])
            # TODO: Add family
            await ctx.send(embed=em)
            return True
        else:
            if alert:
                await ctx.send(MSG_ENTITY_NOT_FOUND)
            return False

    @kanka.command(name='location')
    async def display_location(self, ctx, location_id, alert=True):
        """Display selected location."""
        # TODO: Attributes and relations
        try:
            location_id = int(location_id)
        except ValueError:
            location_id = await self._search('location', await self._active(ctx),
                                             location_id)
            if location_id == 'NoResults':
                if alert:
                    await ctx.send(MSG_ENTITY_NOT_FOUND)
                return False
        location = await self._get_entity(await self._active(ctx), 'locations', location_id)
        if not await self._check_private(ctx.guild, location):
            em = discord.Embed(title=location.name,
                               description=await self._parse_entry(ctx, await self._active(ctx), location),
                               url='https://kanka.io/{lang}/campaign/'
                                   '{cmpgn_id}'
                                   '/locations/'
                                   '{location_id}'
                               .format(
                                   lang=await self._language(ctx),
                                   cmpgn_id=await self._active(ctx),
                                   location_id=location_id),
                               colour=discord.Color.blue())
            em.set_image(url=location.image)
            if location.map is not None:
                em.add_field(name='Map', value='[View Map](https://kanka.io/{lang}/campaign/'
                                               '{cmpgn_id}'
                                               '/locations/'
                                               '{location_id}'
                                               '/map)'
                             .format(
                    lang=await self._language(ctx),
                    cmpgn_id=await self._active(ctx),
                    location_id=location_id
                )
                             )
            if location.parent_location_id is not None:
                em.add_field(name='Parent Location',
                             value='[View Parent Location](https://kanka.io/{lang}/campaign/{cmpgn_id}/'
                                   'locations/{parent_location_id})'
                             .format(lang=await self._language(ctx),
                                     cmpgn_id=await self._active(ctx),
                                     parent_location_id=location.parent_location_id
                                     )
                             )
            # TODO: Display parent name as link instead of id
            await ctx.send(embed=em)
            return True
        else:
            if alert:
                await ctx.send(MSG_ENTITY_NOT_FOUND)
            return False

    @kanka.command(name='event')
    async def display_event(self, ctx, event_id, alert=True):
        """Display selected event."""
        # TODO: Attributes and relations
        try:
            event_id = int(event_id)
        except ValueError:
            event_id = await self._search('event', await self._active(ctx),
                                          event_id)
            if event_id == 'NoResults':
                if alert:
                    await ctx.send(MSG_ENTITY_NOT_FOUND)
                return False
        event = await self._get_entity(await self._active(ctx), 'events', event_id)
        if not await self._check_private(ctx.guild, event):
            em = discord.Embed(title=event.name,
                               description=await self._parse_entry(ctx, await self._active(ctx), event),
                               url='https://kanka.io/{lang}/campaign/'
                                   '{cmpgn_id}'
                                   '/events/'
                                   '{event_id}'
                               .format(
                                   lang=await self._language(ctx),
                                   cmpgn_id=await self._active(ctx),
                                   event_id=event_id),
                               colour=discord.Color.blue())
            em.set_thumbnail(url=event.image)
            em.add_field(name='Date', value=event.date)
            em.add_field(name='Location',
                         value='[View Location](https://kanka.io/{lang}/campaign/{cmpgn_id}/'
                               'locations/{location_id})'
                         .format(lang=await self._language(ctx),
                                 cmpgn_id=await self._active(ctx),
                                 location_id=event.location_id
                                 )
                         )
            # TODO: Display parent name as link instead of id
            await ctx.send(embed=em)
            return True
        else:
            if alert:
                await ctx.send(MSG_ENTITY_NOT_FOUND)
            return False

    @kanka.command(name='family')
    async def display_family(self, ctx, family_id, alert=True):
        """Display selected family."""
        # TODO: Attributes and relations
        try:
            family_id = int(family_id)
        except ValueError:
            family_id = await self._search('family', await self._active(ctx),
                                           family_id)
            if family_id == 'NoResults':
                if alert:
                    await ctx.send(MSG_ENTITY_NOT_FOUND)
                return False
        family = await self._get_entity(await self._active(ctx), 'families', family_id)
        if not await self._check_private(ctx.guild, family):
            em = discord.Embed(title=family.name,
                               description=await self._parse_entry(ctx, await self._active(ctx), family),
                               url='https://kanka.io/{lang}/campaign/'
                                   '{cmpgn_id}'
                                   '/families/'
                                   '{family_id}'
                               .format(
                                   lang=await self._language(ctx),
                                   cmpgn_id=await self._active(ctx),
                                   family_id=family_id),
                               colour=discord.Color.blue())
            em.set_thumbnail(url=family.image)
            # TODO: Add handling for no location
            em.add_field(name='Location',
                         value='[View Location](https://kanka.io/{lang}/campaign/{cmpgn_id}/'
                               'locations/{location_id})'
                         .format(lang=await self._language(ctx),
                                 cmpgn_id=await self._active(ctx),
                                 location_id=family.location_id
                                 )
                         )
            await ctx.send(embed=em)
            return True
        else:
            if alert:
                await ctx.send(MSG_ENTITY_NOT_FOUND)
            return False

    @kanka.command(name='calendar')
    async def display_calendar(self, ctx, calendar_id, alert=True):
        """Display selected calendar."""
        # TODO: Attributes and relations
        try:
            calendar_id = int(calendar_id)
        except ValueError:
            calendar_id = await self._search('calendar', await self._active(ctx),
                                             calendar_id)
            if calendar_id == 'NoResults':
                if alert:
                    await ctx.send(MSG_ENTITY_NOT_FOUND)
                return False
        calendar = await self._get_entity(await self._active(ctx), 'calendars', calendar_id)
        if not await self._check_private(ctx.guild, calendar):
            em = discord.Embed(title=calendar.name,
                               description=await self._parse_entry(ctx, await self._active(ctx), calendar),
                               url='https://kanka.io/{lang}/campaign/'
                                   '{cmpgn_id}'
                                   '/calendars/'
                                   '{calendar_id}'
                               .format(
                                   lang=await self._language(ctx),
                                   cmpgn_id=await self._active(ctx),
                                   calendar_id=calendar_id),
                               colour=discord.Color.blue())
            em.set_thumbnail(url=calendar.image)
            # TODO: fix these fields. Concatenation error None type. Probably an issue in the class JSON format
            em.add_field(name='Date', value=calendar.date + calendar.suffix)
            em.add_field(name='Months', value=calendar.get_month_names())
            em.add_field(name='Length', value=calendar.get_year_length())
            em.add_field(name='Days', value=calendar.get_weekdays())
            await ctx.send(embed=em)
            return True
        else:
            if alert:
                await ctx.send(MSG_ENTITY_NOT_FOUND)
            return False

    @kanka.command(name='diceroll')
    async def display_diceroll(self, ctx, diceroll_id, alert=True):
        """Display selected dice roll."""
        # TODO: Attributes and relations
        try:
            diceroll_id = int(diceroll_id)
        except ValueError:
            diceroll_id = await self._search('diceroll', await self._active(ctx),
                                             diceroll_id)
            if diceroll_id == 'NoResults':
                if alert:
                    await ctx.send(MSG_ENTITY_NOT_FOUND)
                return False
        diceroll = await self._get_diceroll(await self._active(ctx), diceroll_id)
        if not await self._check_private(ctx.guild, diceroll):
            em = discord.Embed(title=diceroll.name,
                               description=diceroll.parameters,
                               url='https://kanka.io/{lang}/campaign/'
                                   '{cmpgn_id}'
                                   '/dice_rolls/'
                                   '{diceroll_id}'
                               .format(
                                   lang=await self._language(ctx),
                                   cmpgn_id=await self._active(ctx),
                                   diceroll_id=diceroll_id),
                               colour=discord.Color.blue())
            em.set_thumbnail(url=diceroll.image)
            await ctx.send(embed=em)
        else:
            await ctx.send(MSG_ENTITY_NOT_FOUND)

    @kanka.command(name='item')
    async def display_item(self, ctx, item_id, alert=True):
        """Display selected item."""
        # TODO: Attributes and relations
        try:
            item_id = int(item_id)
        except ValueError:
            item_id = await self._search('item', await self._active(ctx), item_id)
            if item_id == 'NoResults':
                if alert:
                    await ctx.send(MSG_ENTITY_NOT_FOUND)
                return False
        item = await self._get_entity(await self._active(ctx), 'items', item_id)
        if not await self._check_private(ctx.guild, item):
            em = discord.Embed(title=item.name,
                               description=await self._parse_entry(ctx, await self._active(ctx), item),
                               url='https://kanka.io/{lang}/campaign/'
                                   '{cmpgn_id}'
                                   '/items/'
                                   '{item_id}'
                               .format(
                                   lang=await self._language(ctx),
                                   cmpgn_id=await self._active(ctx),
                                   item_id=item_id),
                               colour=discord.Color.blue())
            em.set_image(url=item.image)
            em.add_field(name='Owner',
                         value='[View Owner](https://kanka.io/{lang}/campaign/{cmpgn_id}/'
                               'characters/{character_id})'
                         .format(lang=await self._language(ctx),
                                 cmpgn_id=await self._active(ctx),
                                 character_id=item.character_id
                                 ))
            em.add_field(name='Location',
                         value='[View Location](https://kanka.io/{lang}/campaign/{cmpgn_id}/'
                               'locations/{location_id})'
                         .format(lang=await self._language(ctx),
                                 cmpgn_id=await self._active(ctx),
                                 location_id=item.location_id
                                 )
                         )
            await ctx.send(embed=em)
            return True
        else:
            if alert:
                await ctx.send(MSG_ENTITY_NOT_FOUND)
            return False

    @kanka.command(name='journal')
    async def display_journal(self, ctx, journal_id, alert=True):
        """Display selected journal."""
        # TODO: Attributes and relations
        try:
            journal_id = int(journal_id)
        except ValueError:
            journal_id = await self._search('journal', await self._active(ctx),
                                            journal_id)
            if journal_id == 'NoResults':
                if alert:
                    await ctx.send(MSG_ENTITY_NOT_FOUND)
                return False
        journal = await self._get_entity(await self._active(ctx), 'journals', journal_id)
        if not await self._check_private(ctx.guild, journal):
            em = discord.Embed(title=journal.name,
                               description=await self._parse_entry(ctx, await self._active(ctx), journal),
                               url='https://kanka.io/{lang}/campaign/'
                                   '{cmpgn_id}'
                                   '/journals/'
                                   '{journal_id}'
                               .format(
                                   lang=await self._language(ctx),
                                   cmpgn_id=await self._active(ctx),
                                   journal_id=journal_id),
                               colour=discord.Color.blue())
            em.set_thumbnail(url=journal.image)
            em.add_field(name='Author',
                         value='[View Author](https://kanka.io/{lang}/campaign/{cmpgn_id}/'
                               'characters/{character_id})'
                         .format(lang=await self._language(ctx),
                                 cmpgn_id=await self._active(ctx),
                                 character_id=journal.character_id
                                 ))
            em.add_field(name='Date', value=journal.date)
            em.add_field(name='Type', value=journal.kind)
            await ctx.send(embed=em)
            return True
        else:
            if alert:
                await ctx.send(MSG_ENTITY_NOT_FOUND)
            return False

    @kanka.command(name='organisation')
    async def display_organisation(self, ctx, organisation_id, alert=True):
        """Display selected organisation."""
        # TODO: Attributes and relations
        # TODO: Get and list members
        try:
            organisation_id = int(organisation_id)
        except ValueError:
            organisation_id = await self._search('organisation',
                                                 await self._active(ctx),
                                                 organisation_id)
            if organisation_id == 'NoResults':
                if alert:
                    await ctx.send(MSG_ENTITY_NOT_FOUND)
                return False
        organisation = await self._get_entity(await self._active(ctx), 'organisations', organisation_id)
        if not await self._check_private(ctx.guild, organisation):
            em = discord.Embed(title=organisation.name,
                               description=await self._parse_entry(ctx, await self._active(ctx), organisation),
                               url='https://kanka.io/{lang}/campaign/'
                                   '{cmpgn_id}'
                                   '/organisations/'
                                   '{organisation_id}'
                               .format(
                                   lang=await self._language(ctx),
                                   cmpgn_id=await self._active(ctx),
                                   organisation_id=organisation_id),
                               colour=discord.Color.blue())
            em.set_thumbnail(url=organisation.image)
            em.add_field(name='Location',
                         value='[View Location](https://kanka.io/{lang}/campaign/{cmpgn_id}/'
                               'locations/{location_id})'
                         .format(lang=await self._language(ctx),
                                 cmpgn_id=await self._active(ctx),
                                 location_id=organisation.location_id
                                 ))
            em.add_field(name='Members', value=organisation.members)
            em.add_field(name='Type', value=organisation.kind)
            await ctx.send(embed=em)
            return True
        else:
            if alert:
                await ctx.send(MSG_ENTITY_NOT_FOUND)
            return False

    @kanka.command(name='quest')
    async def display_quest(self, ctx, quest_id, alert=True):
        """Display selected quest."""
        # TODO: Attributes and relations
        # TODO: Get and list members
        try:
            quest_id = int(quest_id)
        except ValueError:
            quest_id = await self._search('quest', await self._active(ctx),
                                          quest_id)
            if quest_id == 'NoResults':
                if alert:
                    await ctx.send(MSG_ENTITY_NOT_FOUND)
                return False
        quest = await self._get_entity(await self._active(ctx), 'quests', quest_id)
        if not await self._check_private(ctx.guild, quest):
            em = discord.Embed(title=quest.name,
                               description=await self._parse_entry(ctx, await self._active(ctx), quest),
                               url='https://kanka.io/{lang}/campaign/'
                                   '{cmpgn_id}'
                                   '/quests/'
                                   '{quest_id}'
                               .format(
                                   lang=await self._language(ctx),
                                   cmpgn_id=await self._active(ctx),
                                   quest_id=quest_id),
                               colour=discord.Color.blue())
            em.set_thumbnail(url=quest.image)
            em.add_field(name='Instigator',
                         value='[View Instigator](https://kanka.io/{lang}/campaign/{cmpgn_id}/'
                               'characters/{character_id})'
                         .format(lang=await self._language(ctx),
                                 cmpgn_id=await self._active(ctx),
                                 character_id=quest.character_id
                                 ))
            em.add_field(name='Completed', value=quest.is_completed)
            em.add_field(name='Characters', value=quest.characters)
            em.add_field(name='Parent Quest',
                         value='[View Parent Quest](https://kanka.io/{lang}/campaign/{cmpgn_id}/'
                               'quests/{quest_id})'
                         .format(lang=await self._language(ctx),
                                 cmpgn_id=await self._active(ctx),
                                 quest_id=quest.parent_quest_id
                                 ))
            em.add_field(name='Locations', value=quest.locations)
            em.add_field(name='Type', value=quest.kind)
            await ctx.send(embed=em)
            return True
        else:
            if alert:
                await ctx.send(MSG_ENTITY_NOT_FOUND)
            return False

    @kanka.command(name='tag')
    async def display_tag(self, ctx, tag_id, alert=True):
        """Display selected tag."""
        # TODO: Attributes and relations
        # TODO: Get and list children and subcategories
        try:
            tag_id = int(tag_id)
        except ValueError:
            tag_id = await self._search('tag', await self._active(ctx),
                                        tag_id)
            if tag_id == 'NoResults':
                if alert:
                    await ctx.send(MSG_ENTITY_NOT_FOUND)
                return False
        tag = await self._get_entity(await self._active(ctx), 'tags', tag_id)
        if not await self._check_private(ctx.guild, tag):
            em = discord.Embed(title=tag.name,
                               description=await self._parse_entry(ctx, await self._active(ctx), tag),
                               url='https://kanka.io/{lang}/campaign/'
                                   '{cmpgn_id}'
                                   '/tags/'
                                   '{tag_id}'
                               .format(
                                   lang=await self._language(ctx),
                                   cmpgn_id=await self._active(ctx),
                                   tag_id=tag_id),
                               colour=discord.Color.blue())
            em.set_thumbnail(url=tag.image)
            em.add_field(name='Parent Tag',
                         value='[View Parent Tag](https://kanka.io/{lang}/campaign/{cmpgn_id}/'
                               'tags/{tag_id})'
                         .format(lang=await self._language(ctx),
                                 cmpgn_id=await self._active(ctx),
                                 tag_id=tag.tag_id
                                 ))
            em.add_field(name='Type', value=tag.kind)
            await ctx.send(embed=em)
            return True
        else:
            if alert:
                await ctx.send(MSG_ENTITY_NOT_FOUND)
            return False

    @kanka.command(name='note')
    async def display_note(self, ctx, note_id, alert=True):
        """Display selected note."""
        # TODO: Attributes and relations
        try:
            note_id = int(note_id)
        except ValueError:
            note_id = await self._search('note', await self._active(ctx),
                                         note_id)
            if note_id == 'NoResults':
                if alert:
                    await ctx.send(MSG_ENTITY_NOT_FOUND)
                return False
        note = await self._get_entity(await self._active(ctx), 'notes', note_id)
        if not await self._check_private(ctx.guild, note):
            em = discord.Embed(title=note.name,
                               description=await self._parse_entry(ctx, await self._active(ctx), note),
                               url='https://kanka.io/{lang}/campaign/'
                                   '{cmpgn_id}'
                                   '/notes/'
                                   '{note_id}'
                               .format(
                                   lang=await self._language(ctx),
                                   cmpgn_id=await self._active(ctx),
                                   note_id=note_id),
                               colour=discord.Color.blue())
            em.set_thumbnail(url=note.image)
            em.add_field(name='Type', value=note.kind)
            await ctx.send(embed=em)
            return True
        else:
            if alert:
                await ctx.send(MSG_ENTITY_NOT_FOUND)
            return False

    @kanka.command(name='race')
    async def display_race(self, ctx, race_id, alert=True):
        # TODO: Attributes and relations
        try:
            race_id = int(race_id)
        except ValueError:
            race_id = await self._search('race', await self._active(ctx),
                                         race_id)
            if race_id == 'NoResults':
                if alert:
                    await ctx.send(MSG_ENTITY_NOT_FOUND)
                return False
        race = await self._get_entity(await self._active(ctx), 'races', race_id)
        if not await self._check_private(ctx.guild, race):
            em = discord.Embed(title=race.name,
                               description=await self._parse_entry(ctx, await self._active(ctx), race),
                               url='https://kanka.io/{lang}/campaign/'
                                   '{cmpgn_id}'
                                   '/races/'
                                   '{race_id}'
                               .format(
                                   lang=await self._language(ctx),
                                   cmpgn_id=await self._active(ctx),
                                   race_id=race_id),
                               colour=discord.Color.blue())
            em.set_thumbnail(url=race.image)
            em.add_field(name='Type', value=race.kind)
            if race.parent_race_id is not None:
                em.add_field(name='Parent Race',
                             value='[View Parent Race](https://kanka.io/{lang}/campaign/{cmpgn_id}/'
                                   'races/{parent_race_id})'
                             .format(lang=await self._language(ctx),
                                     cmpgn_id=await self._active(ctx),
                                     parent_race_id=race.parent_race_id
                                     )
                             )
            # TODO: Display parent name as link instead of id
            await ctx.send(embed=em)
            return True
        else:
            if alert:
                await ctx.send(MSG_ENTITY_NOT_FOUND)
            return False

    @kanka.command(name='search')
    async def display_search(self, ctx, search_id):
        """Display selected Entity."""

        if await self.display_character(ctx, search_id, False):
            return
        elif await self.display_location(ctx, search_id, False):
            return
        elif await self.display_item(ctx, search_id, False):
            return
        elif await self.display_organisation(ctx, search_id, False):
            return
        elif await self.display_quest(ctx, search_id, False):
            return
        elif await self.display_family(ctx, search_id, False):
            return
        elif await self.display_note(ctx, search_id, False):
            return
        elif await self.display_event(ctx, search_id, False):
            return
        elif await self.display_race(ctx, search_id, False):
            return
        elif await self.display_calendar(ctx, search_id, False):
            return
        elif await self.display_tag(ctx, search_id, False):
            return
        elif await self.display_journal(ctx, search_id, False):
            return
        else:
            await ctx.send(MSG_ENTITY_NOT_FOUND)

    @kanka.command(name='refresh')
    async def load_id_map(self, ctx):
        """Reload IDs for new Entities. May help reduce loading times."""
        await ctx.send('Loading Entity info...')
        await self._load_entity_id_map(await self._active(ctx))
        await ctx.send(str(len(ID_MAP)) + ' Entities loaded.')

    @commands.group(name='kankaset')
    @checks.admin_or_permissions(manage_guild=True)
    async def kankaset(self, ctx):
        """Configuration commands for KankaView"""

    @kankaset.command(name='token')
    async def set_token(self, ctx, token: str):
        """Set API token ('Personal Access Token'). Do not include 'Bearer '.
        Be aware that this token is stored in plaintext by the bot."""
        if token[:7] != 'Bearer ':
            token = 'Bearer ' + token
        await self.config.token.set(token)
        await self._set_headers()
        await ctx.send('API token set.')

    @kankaset.command(name='language')
    async def set_language(self, ctx, language: str):
        """Set language used in links. Valid language codes are en, de, en-US,
        es, fr, pt-BR"""
        LANGUAGES = ['en', 'de', 'en-US', 'es', 'fr', 'pt-BR']
        if language in LANGUAGES:
            await self.config.guild(ctx.guild).language.set(language)
            await ctx.send('Language set to {}'.format(language))
        else:
            await ctx.send_help()

    @kankaset.command(name='toggleprivate')
    async def hide_private(self, ctx):
        """Toggle if private entities are hidden."""
        hide_private = await self.config.guild(ctx.guild).hide_private()
        if hide_private:
            await self.config.guild(ctx.guild).hide_private.set(False)
            await ctx.send('Now showing private entities.')
        else:
            await self.config.guild(ctx.guild).hide_private.set(True)
            await ctx.send('Now hiding private entities.')

    @kankaset.command(name='reset')
    async def restore_default_settings(self, ctx):
        """Return to default settings."""
        # TODO: Add confirmation before deletion for safety
        await self.config.guild(ctx.guild).clear()
        await ctx.send('Server specific settings reset to default.')

    @kankaset.command(name='forceheaders')
    async def force_headers(self, ctx):
        """Forces header creation, resolves some issues."""
        await self._set_headers()
        await ctx.send('Set headers.')
