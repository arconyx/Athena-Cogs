from redbot.core import commands, Config, checks
import discord
import aiohttp
import tomd

DEFAULT_SETTINGS = {'token': None, 'language': 'en', 'hide_private': True}
REQUEST_PATH = 'https://kanka.io/api/1.0/'
STORAGE_PATH = 'https://kanka-user-assets.s3.eu-central-1.amazonaws.com/'
MSG_ENTITY_NOT_FOUND = 'Entity not found.'

# TODO: OAuth user tokens?


class Campaign:
    def __init__(self, json_data):
        self.id = json_data['id']
        self.name = json_data['name']
        self.locale = json_data['locale']
        self.entry = tomd.convert(json_data['entry'])
        if len(self.entry) > 2048:
            self.entry = self.entry[:2045] + '...'
        if json_data['image']:
            self.image = STORAGE_PATH + json_data['image']
        else:
            self.image = ''
        self.visibility = json_data['visibility']
        self.created_at = json_data['created_at']
        self.updated_at = json_data['updated_at']
        self.members = json_data['members']['data']


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
        if json_data['image']:
            self.image = STORAGE_PATH + json_data['image']
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
        # Entry length limit due to Discord embed rules
        if len(self.entry) > 2048:
            self.entry = self.entry[:2045] + '...'
        self.id = json_data['id']
        if json_data['image']:
            self.image = STORAGE_PATH + json_data['image']
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


class Location(Entity):
    def __init__(self, campaign_id, json_data):
        super(Location, self).__init__(campaign_id, json_data)
        self.parent_location_id = json_data['parent_location_id']


class Event(Entity):
    def __init__(self, campaign_id, json_data):
        super(Event, self).__init__(campaign_id, json_data)
        self.date = json_data['date']
        self.location_id = json_data['location_id']


class Family(Entity):
    def __init__(self, campaign_id, json_data):
        super(Family, self).__init__(campaign_id, json_data)
        self.location_id = json_data['location_id']


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


class Journal(Entity):
    def __init__(self, campaign_id, json_data):
        super(Journal, self).__init__(campaign_id, json_data)
        self.date = json_data['date']
        self.character_id = json_data['character_id']


class Organisation(Entity):
    def __init__(self, campaign_id, json_data):
        super(Organisation, self).__init__(campaign_id, json_data)
        self.location_id = json_data['location_id']
        self.members = json_data['members']


class Quest(Entity):
    def __init__(self, campaign_id, json_data):
        super(Quest, self).__init__(campaign_id, json_data)
        self.character_id = json_data['character_id']
        self.characters = json_data['characters']
        self.is_completed = json_data['is_completed']
        self.locations = json_data['locations']
        self.parent_quest_id = json_data['quest_id']


class Tag(Entity):
    def __init__(self, campaign_id, json_data):
        super(Tag, self).__init__(campaign_id, json_data)
        self.tag_id = json_data['tag_id']


class Note(Entity):
    def __init__(self, campaign_id, json_data):
        super(Note, self).__init__(campaign_id, json_data)
        self.is_pinned = json_data['is_pinned']


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

    async def _get_character(self, campaign_id, character_id):
        # TODO: Search by name
        async with self.session.get('{base_url}campaigns/'
                                    '{campaign_id}'
                                    '/characters/'
                                    '{character_id}'.format(
                                        base_url=REQUEST_PATH,
                                        campaign_id=campaign_id,
                                        character_id=character_id)
                                    ) as r:
            j = await r.json()
            return Character(campaign_id, j['data'])

    async def _get_location(self, campaign_id, location_id):
        # TODO: Search by name
        async with self.session.get('{base_url}campaigns/'
                                    '{campaign_id}'
                                    '/locations/'
                                    '{location_id}'.format(
                                        base_url=REQUEST_PATH,
                                        campaign_id=campaign_id,
                                        location_id=location_id)
                                    ) as r:
            j = await r.json()
            return Location(campaign_id, j['data'])

    async def _get_event(self, campaign_id, event_id):
        # TODO: Search by name
        async with self.session.get('{base_url}campaigns/'
                                    '{campaign_id}'
                                    '/events/'
                                    '{event_id}'.format(
                                        base_url=REQUEST_PATH,
                                        campaign_id=campaign_id,
                                        event_id=event_id)
                                    ) as r:
            j = await r.json()
            return Event(campaign_id, j['data'])

    async def _get_family(self, campaign_id, family_id):
        # TODO: Search by name
        async with self.session.get('{base_url}campaigns/'
                                    '{campaign_id}'
                                    '/families/'
                                    '{family_id}'.format(
                                        base_url=REQUEST_PATH,
                                        campaign_id=campaign_id,
                                        family_id=family_id)
                                    ) as r:
            j = await r.json()
            return Family(campaign_id, j['data'])

    async def _get_calendar(self, campaign_id, calendar_id):
        # TODO: Search by name
        async with self.session.get('{base_url}campaigns/'
                                    '{campaign_id}'
                                    '/calendars/'
                                    '{calendar_id}'.format(
                                        base_url=REQUEST_PATH,
                                        campaign_id=campaign_id,
                                        calendar_id=calendar_id)
                                    ) as r:
            j = await r.json()
            return Calendar(campaign_id, j['data'])

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

    async def _get_item(self, campaign_id, item_id):
        # TODO: Search by name
        async with self.session.get('{base_url}campaigns/'
                                    '{campaign_id}'
                                    '/items/'
                                    '{item_id}'.format(
                                        base_url=REQUEST_PATH,
                                        campaign_id=campaign_id,
                                        item_id=item_id)
                                    ) as r:
            j = await r.json()
            return Item(campaign_id, j['data'])

    async def _get_journal(self, campaign_id, journal_id):
        # TODO: Search by name
        async with self.session.get('{base_url}campaigns/'
                                    '{campaign_id}'
                                    '/journals/'
                                    '{journal_id}'.format(
                                        base_url=REQUEST_PATH,
                                        campaign_id=campaign_id,
                                        journal_id=journal_id)
                                    ) as r:
            j = await r.json()
            return Journal(campaign_id, j['data'])

    async def _get_organisation(self, campaign_id, organisation_id):
        # TODO: Search by name
        async with self.session.get('{base_url}campaigns/'
                                    '{campaign_id}'
                                    '/organisations/'
                                    '{organisation_id}'.format(
                                        base_url=REQUEST_PATH,
                                        campaign_id=campaign_id,
                                        organisation_id=organisation_id)
                                    ) as r:
            j = await r.json()
            return Organisation(campaign_id, j['data'])

    async def _get_quest(self, campaign_id, quest_id):
        # TODO: Search by name
        async with self.session.get('{base_url}campaigns/'
                                    '{campaign_id}'
                                    '/quests/'
                                    '{quest_id}'.format(
                                        base_url=REQUEST_PATH,
                                        campaign_id=campaign_id,
                                        quest_id=quest_id)
                                    ) as r:
            j = await r.json()
            return Quest(campaign_id, j['data'])

    async def _get_tag(self, campaign_id, tag_id):
        # TODO: Search by name
        async with self.session.get('{base_url}campaigns/'
                                    '{campaign_id}'
                                    '/tags/'
                                    '{tag_id}'.format(
                                        base_url=REQUEST_PATH,
                                        campaign_id=campaign_id,
                                        tag_id=tag_id)
                                    ) as r:
            j = await r.json()
            return Tag(campaign_id, j['data'])

    async def _get_note(self, campaign_id, note_id):
        # TODO: Search by name
        async with self.session.get('{base_url}campaigns/'
                                    '{campaign_id}'
                                    '/notes/'
                                    '{note_id}'.format(
                                        base_url=REQUEST_PATH,
                                        campaign_id=campaign_id,
                                        note_id=note_id)
                                    ) as r:
            j = await r.json()
            return Note(campaign_id, j['data'])

    async def _search(self, kind, cmpgn_id, query):
        # TODO: Enable after search support releases
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
                           description=campaign.entry,
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

    @kanka.command(name='character')
    async def display_character(self, ctx, character_id):
        """Display selected character."""
        # TODO: Attributes and relations
        try:
            character_id = int(character_id)
        except ValueError:
            character_id = await self._search('character',
                                              await self._active(ctx),
                                              character_id)
            if character_id == 'NoResults':
                await ctx.send(MSG_ENTITY_NOT_FOUND)
                return
        char = await self._get_character(await self._active(ctx), character_id)
        if not await self._check_private(ctx.guild, char):
            em = discord.Embed(title=char.name,
                               description=char.entry,
                               url='https://kanka.io/{lang}/campaign/'
                               '{cmpgn_id}'
                               '/characters/'
                               '{character_id}'
                               .format(
                                   lang=await self._language(ctx),
                                   cmpgn_id=await self._active(ctx),
                                   character_id=character_id),
                               colour=discord.Color.blue())
            em.set_thumbnail(url=char.image)
            em.add_field(name='Title', value=char.title)
            em.add_field(name='Age', value=char.age)
            em.add_field(name='Type', value=char.kind)
            # em.add_field(name='Race', value=char.race)
            em.add_field(name='Is Dead', value=char.is_dead)
            em.add_field(name='Sex', value=char.sex)
            if char.location_id is not None:
                em.add_field(name='Location', value='https://kanka.io/{lang}/'
                             'campaign/'
                             '{cmpgn_id}'
                             '/locations/'
                             '{location_id}'
                             .format(
                                lang=await self._language(ctx),
                                cmpgn_id=await self._active(ctx),
                                location_id=char.location_id))
            # TODO: Add family
            await ctx.send(embed=em)
        else:
            await ctx.send(MSG_ENTITY_NOT_FOUND)

    @kanka.command(name='location')
    async def display_location(self, ctx, location_id):
        """Display selected location."""
        # TODO: Attributes and relations
        try:
            location_id = int(location_id)
        except ValueError:
            location_id = await self._search('location', await self._active(ctx),
                                             location_id)
            if location_id == 'NoResults':
                await ctx.send(MSG_ENTITY_NOT_FOUND)
                return
        location = await self._get_location(await self._active(ctx), location_id)
        if not await self._check_private(ctx.guild, location):
            em = discord.Embed(title=location.name,
                               description=location.entry,
                               url='https://kanka.io/{lang}/campaign/'
                               '{cmpgn_id}'
                               '/locations/'
                               '{location_id}'
                               .format(
                                   lang=await self._language(ctx),
                                   cmpgn_id=await self._active(ctx),
                                   location_id=location_id),
                               colour=discord.Color.blue())
            em.set_thumbnail(url=location.image)
            if location.parent_location_id is not None:
                em.add_field(name='Parent Location',
                             value='https://kanka.io/{lang}/campaign/{cmpgn_id}/'
                             'locations/{parent_location_id}'
                             .format(lang=await self._language(ctx),
                                     cmpgn_id=await self._active(ctx),
                                     parent_location_id=location.parent_location_id
                                     )
                         )
            # TODO: Display parent name as link instead of id
            await ctx.send(embed=em)
        else:
            await ctx.send(MSG_ENTITY_NOT_FOUND)

    @kanka.command(name='event')
    async def display_event(self, ctx, event_id):
        """Display selected event."""
        # TODO: Attributes and relations
        try:
            event_id = int(event_id)
        except ValueError:
            event_id = await self._search('event', await self._active(ctx),
                                          event_id)
            if event_id == 'NoResults':
                await ctx.send(MSG_ENTITY_NOT_FOUND)
                return
        event = await self._get_event(await self._active(ctx), event_id)
        if not await self._check_private(ctx.guild, event):
            em = discord.Embed(title=event.name,
                               description=event.entry,
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
                         value='https://kanka.io/{lang}/campaign/{cmpgn_id}/'
                         'locations/{location_id}'
                         .format(lang=await self._language(ctx),
                                 cmpgn_id=await self._active(ctx),
                                 location_id=event.location_id
                                 )
                         )
            # TODO: Display parent name as link instead of id
            await ctx.send(embed=em)
        else:
            await ctx.send(MSG_ENTITY_NOT_FOUND)

    @kanka.command(name='family')
    async def display_family(self, ctx, family_id):
        """Display selected family."""
        # TODO: Attributes and relations
        try:
            family_id = int(family_id)
        except ValueError:
            family_id = await self._search('family', await self._active(ctx),
                                           family_id)
            if family_id == 'NoResults':
                await ctx.send(MSG_ENTITY_NOT_FOUND)
                return
        family = await self._get_family(await self._active(ctx), family_id)
        if not await self._check_private(ctx.guild, family):
            em = discord.Embed(title=family.name,
                               description=family.entry,
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
                         value='https://kanka.io/{lang}/campaign/{cmpgn_id}/'
                         'locations/{location_id}'
                         .format(lang=await self._language(ctx),
                                 cmpgn_id=await self._active(ctx),
                                 location_id=family.location_id
                                 )
                         )
            await ctx.send(embed=em)
        else:
            await ctx.send(MSG_ENTITY_NOT_FOUND)

    @kanka.command(name='calendar')
    async def display_calendar(self, ctx, calendar_id):
        """Display selected calendar."""
        # TODO: Attributes and relations
        try:
            calendar_id = int(calendar_id)
        except ValueError:
            calendar_id = await self._search('calendar', await self._active(ctx),
                                             calendar_id)
            if calendar_id == 'NoResults':
                await ctx.send(MSG_ENTITY_NOT_FOUND)
                return
        calendar = await self._get_calendar(await self._active(ctx), calendar_id)
        if not await self._check_private(ctx.guild, calendar):
            em = discord.Embed(title=calendar.name,
                               description=calendar.entry,
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
            em.add_field(name='Date', value=calendar.date + calendar.suffix)
            em.add_field(name='Months', value=calendar.get_month_names())
            em.add_field(name='Length', value=calendar.get_year_length())
            em.add_field(name='Days', value=calendar.get_weekdays())
            await ctx.send(embed=em)
        else:
            await ctx.send(MSG_ENTITY_NOT_FOUND)

    @kanka.command(name='diceroll')
    async def display_diceroll(self, ctx, diceroll_id):
        """Display selected dice roll."""
        # TODO: Attributes and relations
        try:
            diceroll_id = int(diceroll_id)
        except ValueError:
            diceroll_id = await self._search('diceroll', await self._active(ctx),
                                             diceroll_id)
            if diceroll_id == 'NoResults':
                await ctx.send(MSG_ENTITY_NOT_FOUND)
                return
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
    async def display_item(self, ctx, item_id):
        """Display selected item."""
        # TODO: Attributes and relations
        try:
            item_id = int(item_id)
        except ValueError:
            item_id = await self._search('item', await self._active(ctx), item_id)
            if item_id == 'NoResults':
                await ctx.send(MSG_ENTITY_NOT_FOUND)
                return
        item = await self._get_item(await self._active(ctx), item_id)
        if not await self._check_private(ctx.guild, item):
            em = discord.Embed(title=item.name,
                               description=item.entry,
                               url='https://kanka.io/{lang}/campaign/'
                               '{cmpgn_id}'
                               '/items/'
                               '{item_id}'
                               .format(
                                   lang=await self._language(ctx),
                                   cmpgn_id=await self._active(ctx),
                                   item_id=item_id),
                               colour=discord.Color.blue())
            em.set_thumbnail(url=item.image)
            em.add_field(name='Owner',
                         value='https://kanka.io/{lang}/campaign/{cmpgn_id}/'
                         'characters/{character_id}'
                         .format(lang=await self._language(ctx),
                                 cmpgn_id=await self._active(ctx),
                                 character_id=item.character_id
                                 ))
            em.add_field(name='Location',
                         value='https://kanka.io/{lang}/campaign/{cmpgn_id}/'
                         'locations/{location_id}'
                         .format(lang=await self._language(ctx),
                                 cmpgn_id=await self._active(ctx),
                                 location_id=item.location_id
                                 )
                         )
            await ctx.send(embed=em)
        else:
            await ctx.send(MSG_ENTITY_NOT_FOUND)

    @kanka.command(name='journal')
    async def display_journal(self, ctx, journal_id):
        """Display selected journal."""
        # TODO: Attributes and relations
        try:
            journal_id = int(journal_id)
        except ValueError:
            journal_id = await self._search('journal', await self._active(ctx),
                                            journal_id)
            if journal_id == 'NoResults':
                await ctx.send(MSG_ENTITY_NOT_FOUND)
                return
        journal = await self._get_journal(await self._active(ctx), journal_id)
        if not await self._check_private(ctx.guild, journal):
            em = discord.Embed(title=journal.name,
                               description=journal.entry,
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
                         value='https://kanka.io/{lang}/campaign/{cmpgn_id}/'
                         'characters/{character_id}'
                         .format(lang=await self._language(ctx),
                                 cmpgn_id=await self._active(ctx),
                                 character_id=journal.character_id
                                 ))
            em.add_field(name='Date', value=journal.date)
            em.add_field(name='Type', value=journal.kind)
            await ctx.send(embed=em)
        else:
            await ctx.send(MSG_ENTITY_NOT_FOUND)

    @kanka.command(name='organisation')
    async def display_organisation(self, ctx, organisation_id):
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
                await ctx.send(MSG_ENTITY_NOT_FOUND)
                return
        organisation = await self._get_organisation(await self._active(ctx),
                                                    organisation_id)
        if not await self._check_private(ctx.guild, organisation):
            em = discord.Embed(title=organisation.name,
                               description=organisation.entry,
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
                         value='https://kanka.io/{lang}/campaign/{cmpgn_id}/'
                         'locations/{location_id}'
                         .format(lang=await self._language(ctx),
                                 cmpgn_id=await self._active(ctx),
                                 location_id=organisation.location_id
                                 ))
            em.add_field(name='Members', value=organisation.members)
            em.add_field(name='Type', value=organisation.kind)
            await ctx.send(embed=em)
        else:
            await ctx.send(MSG_ENTITY_NOT_FOUND)

    @kanka.command(name='quest')
    async def display_quest(self, ctx, quest_id):
        """Display selected quest."""
        # TODO: Attributes and relations
        # TODO: Get and list members
        try:
            quest_id = int(quest_id)
        except ValueError:
            quest_id = await self._search('quest', await self._active(ctx),
                                          quest_id)
            if quest_id == 'NoResults':
                await ctx.send(MSG_ENTITY_NOT_FOUND)
                return
        quest = await self._get_quest(await self._active(ctx), quest_id)
        if not await self._check_private(ctx.guild, quest):
            em = discord.Embed(title=quest.name,
                               description=quest.entry,
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
                         value='https://kanka.io/{lang}/campaign/{cmpgn_id}/'
                         'characters/{character_id}'
                         .format(lang=await self._language(ctx),
                                 cmpgn_id=await self._active(ctx),
                                 character_id=quest.character_id
                                 ))
            em.add_field(name='Completed', value=quest.is_completed)
            em.add_field(name='Characters', value=quest.characters)
            em.add_field(name='Parent Quest',
                         value='https://kanka.io/{lang}/campaign/{cmpgn_id}/'
                         'quests/{quest_id}'
                         .format(lang=await self._language(ctx),
                                 cmpgn_id=await self._active(ctx),
                                 quest_id=quest.parent_quest_id
                                 ))
            em.add_field(name='Locations', value=quest.locations)
            em.add_field(name='Type', value=quest.kind)
            await ctx.send(embed=em)
        else:
            await ctx.send(MSG_ENTITY_NOT_FOUND)

    @kanka.command(name='tag')
    async def display_tag(self, ctx, tag_id):
        """Display selected tag."""
        # TODO: Attributes and relations
        # TODO: Get and list children and subcategories
        try:
            tag_id = int(tag_id)
        except ValueError:
            tag_id = await self._search('tag', await self._active(ctx),
                                        tag_id)
            if tag_id == 'NoResults':
                await ctx.send(MSG_ENTITY_NOT_FOUND)
                return
        tag = await self._get_tag(await self._active(ctx), tag_id)
        if not await self._check_private(ctx.guild, tag):
            em = discord.Embed(title=tag.name,
                               description=tag.entry,
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
            em.add_field(name='Parent tag',
                         value='https://kanka.io/{lang}/campaign/{cmpgn_id}/'
                         'tags/{tag_id}'
                         .format(lang=await self._language(ctx),
                                 cmpgn_id=await self._active(ctx),
                                 tag_id=tag.tag_id
                                 ))
            em.add_field(name='Type', value=tag.kind)
            await ctx.send(embed=em)
        else:
            await ctx.send(MSG_ENTITY_NOT_FOUND)

    @kanka.command(name='note')
    async def display_note(self, ctx, note_id):
        """Display selected note."""
        # TODO: Attributes and relations
        # TODO: Get and list children and subcategories
        try:
            note_id = int(note_id)
        except ValueError:
            note_id = await self._search('note', await self._active(ctx),
                                         note_id)
            if note_id == 'NoResults':
                await ctx.send(MSG_ENTITY_NOT_FOUND)
                return
        note = await self._get_note(await self._active(ctx), note_id)
        if not await self._check_private(ctx.guild, note):
            em = discord.Embed(title=note.name,
                               description=note.entry,
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
            em.add_field(name='Is Pinned', value=note.is_pinned)
            em.add_field(name='Type', value=note.kind)
            await ctx.send(embed=em)
        else:
            await ctx.send(MSG_ENTITY_NOT_FOUND)

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
