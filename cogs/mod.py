# quick moderation based commands
"""
Notes
- make sure commands work in unison with each other with muting
"""

from os import path
import json
from typing import *
from datetime import datetime, timedelta
import asyncio
import re
from time import time as now

from discord.ext import commands
import discord
from discord.ext.commands import Greedy

from utils import utils, colors


cache = {}  # Keep track of what commands are still being ran
            # This should empty out as quickly as it's filled

def check_if_running():
    """ Checks if the command is already in progress """
    async def predicate(ctx):
        # with open(fp, 'r') as f:
        #     cache = json.load(f)  # type: dict
        cmd = ctx.command.name
        if cmd not in cache:
            cache[cmd] = []
        check_result = ctx.guild.id not in cache[cmd]
        if not check_result:
            await ctx.send('That command is already running >:(')
        return check_result
    return commands.check(predicate)


def has_required_permissions(**kwargs):
    """ Permission check with support for usermod, rolemod, and role specific cmd access """
    async def predicate(ctx):
        with open('./data/userdata/moderation.json', 'r') as f:
            config = json.load(f)  # type: dict
        cls = globals()["cls"]  # type: Moderation
        if str(ctx.guild.id) not in config:
            config[str(ctx.guild.id)] = cls.template
        config = config[str(ctx.guild.id)]  # type: dict
        cmd = ctx.command.name
        for command, dat in config['commands'].items():
            for c, subs in cls.subs.items():
                if cmd in subs:
                    cmd = command
                    break
        if cmd in config['commands']:
            allowed = config['commands'][cmd]  # type: dict
            if ctx.author.id in allowed['users']:
                return True
            if any(role.id in allowed['roles'] for role in ctx.author.roles):
                return True
        if ctx.author.id in config['usermod']:
            return True
        if any(r.id in config['rolemod'] for r in ctx.author.roles):
            return True
        perms = ctx.author.guild_permissions
        return all((perm, value) in list(perms) for perm, value in kwargs.items())
    return commands.check(predicate)


def has_warn_permission():
    async def predicate(ctx):
        cls = globals()["cls"]  # type: Moderation
        config = cls.template
        guild_id = str(ctx.guild.id)
        if guild_id in cls.config:
            config = cls.config[guild_id]
        if ctx.author.id in config['commands']['warn']:
            return True
        elif ctx.author.guild_permissions.administrator:
            return True
    return commands.check(predicate)


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.fp = './static/mod-cache.json'
        self.path = './data/userdata/moderation.json'
        self.config = {}
        self.tasks = {}
        if path.isfile(self.path):
            with open(self.path, 'r') as f:
                self.config = json.load(f)  # type: dict

        # Add or remove any missing/unused key/values
        # this is for ease of updating json as it's developed
        for guild_id, config in self.config.items():
            for key, values in self.template.items():
                if key not in config:
                    config[key] = values
            for key, values in config.items():
                if key not in self.template:
                    del config[key]
            self.config[guild_id] = config

        self.subs = {
            "warn": ['delwarn', 'clearwarns'],
            "mute": ['unmute']
        }

    @property
    def template(self):
        return {
            "usermod": [],  # Users with access to all mod commands
            "rolemod": [],  # Roles with access to all mod commands
            "commands": {
                "warn": {'users': [], 'roles': []},
                "purge": {'users': [], 'roles': []},
                "mute": {'users': [], 'roles': []},
                "kick": {'users': [], 'roles': []},
                "ban": {'users': [], 'roles': []}
            },
            "warns": {},
            "warns_config": {},
            "mute_role": None,  # type: Optional[None, discord.Role.id]
            "timers": {},
            "mute_timers": {}
        }

    def save_data(self):
        with open(self.path, 'w') as f:
            json.dump(self.config, f)

    @commands.command(name="convert-mod")
    @commands.is_owner()
    async def convert_moderation_dat(self, ctx):
        cog = self.bot.get_cog("Mod")
        for guild_id, warns in cog.warns.items():
            self.config[guild_id] = self.template
            self.config[guild_id]["warns"] = warns
        await ctx.send("Converted warns")
        for guild_id, timers in cog.timers["mute"].items():
            if guild_id not in self.config:
                self.config[guild_id] = self.template
            self.config[guild_id]["mute_timers"] = timers
        await ctx.send("Converted mute timers")
        for guild_id, timers in cog.timers.items():
            if not guild_id.isdigit():
                continue
            if guild_id not in self.config:
                self.config[guild_id] = self.template
            self.config[guild_id]["timers"] = timers
        await ctx.send("Converted warn timers")
        for guild_id, mods in cog.mods.items():
            if guild_id not in self.config:
                self.config[guild_id] = self.template
            self.config[guild_id]["usermod"] = mods
        await ctx.send("Converted usermods")

    async def cog_before_invoke(self, ctx):
        """ Index commands that are running """
        # if not path.isfile(self.fp):
        #     with open(self.fp, 'w') as f:
        #         json.dump({}, f, indent=2)
        # with open(self.fp, 'r') as f:
        #     cache = json.load(f)  # type: dict
        cmd = ctx.command.name
        if cmd not in cache:
            cache[cmd] = []
        if ctx.guild.id not in cache[cmd]:
            cache[cmd].append(ctx.guild.id)
        # with open(self.fp, 'w') as f:
        #     json.dump(cache, f, indent=2)
        if str(ctx.guild.id) not in self.config:
            self.config[str(ctx.guild.id)] = self.template
            self.save_data()
        ctx.cls = self

    async def cog_after_invoke(self, ctx):
        """ Index commands that are running """
        # with open(self.fp, 'r') as f:
        #     cache = json.load(f)  # type: dict
        cmd = ctx.command.name
        cache[cmd].remove(ctx.guild.id)
        # with open(self.fp, 'w') as f:
        #     json.dump(cache, f, indent=2)

    def save_config(self, config):
        """ Save things like channel restrictions """
        with open('./data/userdata/config.json', 'w') as f:
            json.dump(config, f, ensure_ascii=False)

    @commands.command(name="mute-role", aliases=["muterole", "set-mute-role", "setmuterole", "set-mute", "setmute"])
    @commands.guild_only()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.has_permissions(manage_roles=True)
    async def mute_role(self, ctx, *, role):
        role = await self.bot.utils.get_role(ctx, role)
        if not role:
            return await ctx.send("Role not found")
        if role.position >= ctx.author.top_role.position and not ctx.author.id == ctx.guild.owner.id:
            return await ctx.send("That role's above your paygrade, take a seat.")
        self.config[str(ctx.guild.id)]["mute_role"] = role.id
        await ctx.send(f"Set the mute role to {role.name}")
        self.save_data()

    @commands.command(name='restrict')
    @commands.guild_only()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def restrict(self, ctx, args=None):
        if not args:
            e = discord.Embed(color=colors.fate())
            e.set_author(name='Channel Restricting')
            e.description = 'Prevents everyone except mods from using commands'
            e.add_field(name='Usage', value='.restrict #channel_mention\n'
                                            '.unrestrict #channel_mention\n.restricted')
            return await ctx.send(embed=e)
        guild_id = str(ctx.guild.id)
        config = self.bot.get_config  # type: dict
        if 'restricted' not in config:
            config['restricted'] = {}
        if guild_id not in config['restricted']:
            config['restricted'][guild_id] = {
                'channels': [],
                'users': []
            }
        restricted = '**Restricted:**'
        dat = config['restricted'][guild_id]
        for channel in ctx.message.channel_mentions:
            if channel.id in dat['channels']:
                continue
            config['restricted'][guild_id]['channels'].append(channel.id)
            restricted += f'\n{channel.mention}'
        for member in ctx.message.mentions:
            if member.id in dat['users']:
                continue
            config['restricted'][guild_id]['users'].append(member.id)
            restricted += f'\n{member.mention}'
        e = discord.Embed(color=colors.fate(), description=restricted)
        await ctx.send(embed=e)
        self.save_config(config)

    @commands.command(name='unrestrict')
    @commands.guild_only()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def unrestrict(self, ctx):
        guild_id = str(ctx.guild.id)
        config = self.bot.get_config  # type: dict
        if 'restricted' not in config:
            config['restricted'] = {}
        unrestricted = '**Unrestricted:**'
        if guild_id not in config['restricted']:
            return await ctx.send("Nothing's currently restricted")
        dat = config['restricted'][guild_id]
        for channel in ctx.message.channel_mentions:
            if channel.id in dat['channels']:
                config['restricted'][guild_id]['channels'].remove(channel.id)
                unrestricted += f'\n{channel.mention}'
        for member in ctx.message.mentions:
            if member.id in dat['users']:
                config['restricted'][guild_id]['users'].remove(member.id)
                unrestricted += f'\n{member.mention}'
        e = discord.Embed(color=colors.fate(), description=unrestricted)
        await ctx.send(embed=e)
        self.save_config(config)

    @commands.command(name='addmod')
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(embed_links=True)
    async def addmod(self, ctx, *, user):
        user = utils.get_user(ctx, user)
        if not isinstance(user, discord.Member):
            return await ctx.send('User not found')
        if user.top_role.position >= ctx.author.top_role.position:
            return await ctx.send("That user is above your paygrade, take a seat")
        guild_id = str(ctx.guild.id)
        if user.id in self.config[guild_id]["usermod"]:
            return await ctx.send('That users already a mod')
        self.config[guild_id]["usermod"].append(user.id)
        e = discord.Embed(color=colors.fate())
        e.description = f'Made {user.mention} a mod'
        await ctx.send(embed=e)
        self.save_data()

    @commands.command(name='delmod')
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(embed_links=True)
    async def delmod(self, ctx, *, user):
        user = utils.get_user(ctx, user)
        if not isinstance(user, discord.Member):
            return await ctx.send('User not found')
        if user.top_role.position >= ctx.author.top_role.position:
            return await ctx.send("That user is above your paygrade, take a seat")
        guild_id = str(ctx.guild.id)
        if user.id not in self.config[guild_id]["usermod"]:
            return await ctx.send('That user isn\'t a mod')
        self.config[guild_id]["usermod"].remove(user.id)
        e = discord.Embed(color=colors.fate())
        e.description = f'{user.mention} is no longer a mod'
        await ctx.send(embed=e)
        self.save_data()

    @commands.command(name='restricted')
    @commands.guild_only()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def restricted(self, ctx):
        guild_id = str(ctx.guild.id)
        config = self.bot.get_config  # type: dict
        if guild_id not in config['restricted']:
            return await ctx.send('No restricted channels/users')
        dat = config['restricted'][guild_id]
        e = discord.Embed(color=colors.fate())
        e.set_author(name='Restricted:', icon_url=ctx.author.avatar_url)
        e.description = ''
        if dat['channels']:
            changelog = ''
            for channel_id in dat['channels']:
                channel = self.bot.get_channel(channel_id)
                if not isinstance(channel, discord.TextChannel):
                    position = config['restricted'][guild_id]['channels'].index(channel_id)
                    config['restricted'][guild_id]['channels'].pop(position)
                    self.save_config(config)
                else:
                    changelog += '\n' + channel.mention
            if changelog:
                e.description += changelog
        if dat['users']:
            changelog = ''
            for user_id in dat['users']:
                user = self.bot.get_user(user_id)
                if not isinstance(user, discord.User):
                    position = config['restricted'][guild_id]['users'].index(user_id)
                    config['restricted'][guild_id]['users'].pop(position)
                    self.save_config(config)
                else:
                    changelog += '\n' + user.mention
            if changelog:
                e.description += changelog
        await ctx.send(embed=e)

    @commands.command(name='purge')
    @commands.cooldown(*utils.default_cooldown())
    @check_if_running()
    @has_required_permissions(manage_messages=True)
    @commands.bot_has_permissions(read_message_history=True, manage_messages=True)
    async def purge(self, ctx, *args):
        def help_embed():
            e = discord.Embed(color=colors.fate())
            u = '.purge amount\n' \
                '.purge @user amount\n' \
                '.purge images amount\n' \
                '.purge embeds amount\n' \
                '.purge mentions amount\n' \
                '.purge users amount\n' \
                '.purge bots amount\n' \
                '.purge word/phrase amount'
            e.description = u
            return e

        if not args:
            return await ctx.send(embed=help_embed())
        if args[0].isdigit():  # no special option used
            try:
                amount = int(args[0])
            except:
                return await ctx.send('Invalid amount')
            if amount > 1000:
                return await ctx.send("You cannot purge more than 1000 messages at a time")
            try:
                await ctx.message.channel.purge(limit=amount, before=ctx.message)
                await ctx.send(f'{ctx.author.mention}, successfully purged {amount} messages', delete_after=5)
                return await ctx.message.delete()
            except discord.errors.Forbidden as e:
                await ctx.send(e)
        if len(args) == 1:
            return await ctx.send(embed=help_embed())
        try:
            amount = int(args[1])
        except:
            return await ctx.send('Invalid amount')
        if ctx.message.mentions:
            user = ctx.message.mentions[0]
            if amount > 250:
                return await ctx.send("You cannot purge more than 250 user messages at a time")
            try:
                position = 0
                async for msg in ctx.channel.history(limit=500):
                    if msg.author.id == user.id:
                        if msg.id != ctx.message.id:
                            await msg.delete()
                            position += 1
                            if position == amount:
                                break
                await ctx.send(f'{ctx.author.mention}, purged {position} messages from {user.display_name}', delete_after=5)
                return await ctx.message.delete()
            except discord.errors.Forbidden as e:
                await ctx.send(e)
            return
        option = args[0].lower()  # type: str
        if option == 'image' or option == 'images':
            if amount > 250:
                return await ctx.send("You cannot purge more than 250 images at a time")
            try:
                position = 0
                async for msg in ctx.channel.history(limit=500):
                    if msg.attachments:
                        await msg.delete()
                        position += 1
                        if position == amount:
                            break
                await ctx.send(f"{ctx.author.mention}, purged {position} images", delete_after=5)
                return await ctx.message.delete()
            except discord.errors.Forbidden as e:
                await ctx.send(e)
            return
        if option == 'embed' or option == 'embeds':
            if amount > 250:
                return await ctx.send("You cannot purge more than 250 embeds at a time")
            try:
                position = 0
                async for msg in ctx.channel.history(limit=500):
                    if msg.embeds:
                        await msg.delete()
                        position += 1
                        if position == amount:
                            break
                await ctx.send(f"{ctx.author.mention}, purged {position} embeds", delete_after=5)
                return await ctx.message.delete()
            except discord.errors.Forbidden as e:
                await ctx.send(e)
            return
        if option == 'user' or option == 'users':
            if amount > 250:
                return await ctx.send("You cannot purge more than 250 user messages at a time")
            try:
                position = 0
                async for msg in ctx.channel.history(limit=500):
                    if not msg.author.bot:
                        await msg.delete()
                        position += 1
                        if position == amount:
                            break
                await ctx.send(f"{ctx.author.mention}, purged {position} user messages", delete_after=5)
                return await ctx.message.delete()
            except discord.errors.Forbidden as e:
                await ctx.send(e)
            return
        if option == 'bot' or option == 'bots':
            if amount > 250:
                return await ctx.send("You cannot purge more than 250 bot messages at a time")
            try:
                position = 0
                async for msg in ctx.channel.history(limit=500):
                    if msg.author.bot:
                        await msg.delete()
                        position += 1
                        if position == amount:
                            break
                await ctx.send(f"{ctx.author.mention}, purged {position} bot messages", delete_after=5)
                return await ctx.message.delete()
            except discord.errors.Forbidden as e:
                await ctx.send(e)
            return
        if option == 'mention' or option == 'mentions':
            if amount > 250:
                return await ctx.send("You cannot purge more than 250 mentions at a time")
            try:
                position = 0
                async for msg in ctx.channel.history(limit=500):
                    if msg.mentions:
                        await msg.delete()
                        position += 1
                        if position == amount:
                            break
                await ctx.send(f"{ctx.author.mention}, purged {position} mentions", delete_after=5)
                return await ctx.message.delete()
            except discord.errors.Forbidden as e:
                await ctx.send(e)
            return
        if option == 'reaction' or option == 'reactions':
            if amount > 250:
                return await ctx.send("You cannot purge more than 250 reactions at a time")
            try:
                position = 0
                async for msg in ctx.channel.history(limit=500):
                    if msg.reactions:
                        await msg.clear_reactions()
                        position += 1
                        if position == amount:
                            break
                await ctx.send(f"{ctx.author.mention}, purged {position} reactions", delete_after=5)
                return await ctx.message.delete()
            except discord.errors.Forbidden as e:
                await ctx.send(e)
            return
        phrase = args[0]
        amount = int(args[1])
        if amount > 250:
            return await ctx.send("You cannot purge more than 250 phrases at a time")
        try:
            position = 0
            async for msg in ctx.channel.history(limit=500):
                if phrase.lower() in msg.content.lower():
                    if msg.id != ctx.message.id:
                        await msg.delete()
                        position += 1
                        if position == amount:
                            break
            await ctx.send(f"{ctx.author.mention}, purged {position} messages", delete_after=5)
            return await ctx.message.delete()
        except discord.errors.Forbidden as e:
            await ctx.send(e)

    async def handle_mute_timer(self, guild_id: str, user_id: str, timer_info: dict):
        timer = timer_info["end_time"] - now()
        await asyncio.sleep(timer)  # Switch this to a task
        if user_id in self.config[guild_id]['mute_timers']:
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                del self.config[guild_id]['mute_timers'][user_id]
                return
            user = guild.get_member(int(user_id))
            if not user:
                del self.config[guild_id]['mute_timers'][user_id]
                return
            mute_role = guild.get_role(self.config[guild_id]["mute_role"])
            if not mute_role:
                self.config[guild_id]["mute_role"] = None
                del self.config[guild_id]['mute_timers'][user_id]
                return
            if mute_role in user.roles:
                channel = self.bot.get_channel(timer_info["channel"])
                try:
                    await user.remove_roles(mute_role)
                    await channel.send(f"**Unmuted:** {user.name}")
                except discord.errors.Forbidden:
                    pass
        del self.config[guild_id]['mute_timers'][user_id]
        del self.tasks[guild_id][user_id]
        if not self.tasks[guild_id]:
            del self.tasks[guild_id]

    @commands.command(name='mute', aliases=['shutup', 'fuckoff'])
    @commands.cooldown(*utils.default_cooldown())
    @check_if_running()
    @has_required_permissions(mute_members=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    async def mute(self, ctx, members: Greedy[discord.Member], *, reason="Unspecified"):
        if not members:
            return await ctx.send("**Format:** `.mute {@user} {timer: 2m, 2h, or 2d}`")

        guild_id = str(ctx.guild.id)
        mute_role = None
        async with ctx.channel.typing():
            if self.config[guild_id]["mute_role"]:
                mute_role = ctx.guild.get_role(self.config[guild_id]["mute_role"])
            if not mute_role:
                mute_role = await self.bot.utils.get_role(ctx, "muted")
                if not mute_role:
                    perms = ctx.guild.me.guild_permissions
                    if not perms.manage_channels or not perms.manage_roles:
                        p = self.bot.utils.get_prefix(ctx)
                        return await ctx.send(
                            "No muted role found, and I\'m missing manage_role and manage_channel permissions to set "
                            f"one up. You can set a mute role manually with `{p}mute-role @role` which doesn't "
                            f"have to be a role @mention, and can just be the roles name."
                        )
                    mute_role = await ctx.guild.create_role(name="Muted", color=discord.Color(colors.black()))

                    # Set the overwrites for the mute role
                    for i, channel in enumerate(ctx.guild.text_channels):
                        try:
                            await channel.set_permissions(mute_role, send_messages=False)
                        except discord.errors.Forbidden:
                            pass
                        if i + 1 >= len(ctx.guild.text_channels):  # Prevent sleeping after the last
                            await asyncio.sleep(0.5)
                    for i, channel in enumerate(ctx.guild.voice_channels):
                        try:
                            await channel.set_permissions(mute_role, speak=False)
                        except discord.errors.Forbidden:
                            pass
                        if i + 1 >= len(ctx.guild.voice_channels):  # Prevent sleeping after the last
                            await asyncio.sleep(0.5)

                self.config[guild_id]["mute_role"] = mute_role.id

            # Setup the mute role in channels it's not in
            for i, channel in enumerate(ctx.guild.text_channels):
                if not channel.permissions_for(ctx.guild.me).manage_channels or mute_role in channel.overwrites:
                    continue
                if mute_role not in channel.overwrites:
                    try:
                        await channel.set_permissions(mute_role, send_messages=False)
                    except discord.errors.Forbidden:
                        pass
                    if i + 1 >= len(ctx.guild.text_channels):  # Prevent sleeping after the last
                        await asyncio.sleep(0.5)
            for i, channel in enumerate(ctx.guild.voice_channels):
                if not channel.permissions_for(ctx.guild.me).manage_channels or mute_role in channel.overwrites:
                    continue
                if mute_role not in channel.overwrites:
                    try:
                        await channel.set_permissions(mute_role, speak=False)
                    except discord.errors.Forbidden:
                        pass
                    if i + 1 >= len(ctx.guild.voice_channels):  # Prevent sleeping after the last
                        await asyncio.sleep(0.5)

            timers = []
            timer = expanded_timer = None
            for timer in [re.findall('[0-9]+[smhd]', arg) for arg in reason.split()]:
                timers = [*timers, *timer]
            if timers:
                time_to_sleep = [0, []]
                for timer in timers:
                    reason = str(reason.replace(timer, "")).lstrip(" ").rstrip(" ")
                    raw = ''.join(x for x in list(timer) if x.isdigit())
                    if 'd' in timer:
                        time = int(timer.replace('d', '')) * 60 * 60 * 24
                        repr = 'day'
                    elif 'h' in timer:
                        time = int(timer.replace('h', '')) * 60 * 60
                        repr = 'hour'
                    elif 'm' in timer:
                        time = int(timer.replace('m', '')) * 60
                        repr = 'minute'
                    else:  # 's' in timer
                        time = int(timer.replace('s', ''))
                        repr = 'second'
                    time_to_sleep[0] += time
                    time_to_sleep[1].append(f"{raw} {repr if raw == '1' else repr + 's'}")
                timer, expanded_timer = time_to_sleep
                expanded_timer = ', '.join(expanded_timer)

        if not reason:
            reason = "Unspecified"
        for user in list(members):
            if user.top_role.position >= ctx.author.top_role.position:
                return await ctx.send("That user is above your paygrade, take a seat")
            if mute_role in user.roles:
                return await ctx.send(f'{user.display_name} is already muted')

            if not timers:
                await user.add_roles(mute_role)
                return await ctx.send(f'Muted {user.display_name} for {reason}')

            if timer > 15552000:  # 6 months
                return await ctx.send("No way in hell I'm waiting that long to unmute\n"
                                      "You'll have to do it yourself >:(")
            await user.add_roles(mute_role)
            timer_info = {
                'channel': ctx.channel.id,
                'user': user.id,
                'end_time': now() + timer,
                'mute_role': mute_role.id
            }
            await ctx.send(f"Muted **{user.name}** for {expanded_timer} for {reason}")

            user_id = str(user.id)
            self.config[guild_id]['mute_timers'][user_id] = timer_info
            self.save_data()
            task = self.bot.loop.create_task(self.handle_mute_timer(guild_id, user_id, timer_info))
            if guild_id not in self.tasks:
                self.tasks[guild_id] = {}
            self.tasks[guild_id][user_id] = task

    @commands.command(name="unmute", description="Unblocks users from sending messages")
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.guild_only()
    @has_required_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def unmute(self, ctx, user: discord.Member = None):
        if not user:
            return await ctx.send("**Unmute Usage:**\n.unmute {@user}")
        if user.top_role.position >= ctx.author.top_role.position and ctx.author.id != ctx.guild.owner.id:
            return await ctx.send("That user is above your paygrade, take a seat")
        guild_id = str(ctx.guild.id)
        user_id = str(user.id)
        mute_role = None
        if self.config[guild_id]["mute_role"]:
            mute_role = ctx.guild.get_role(self.config[guild_id]["mute_role"])
            if not mute_role:
                await ctx.send("The configured mute role was deleted, so I'll try to find another")
        if not mute_role:
            mute_role = await self.bot.utils.get_role(ctx, "muted")
        if not mute_role:
            p = self.bot.utils.get_prefix(ctx)
            return await ctx.send(f"No mute role found? If it doesn't have `muted` in the name use `{p}mute-role @role` "
                                  f"which doesn't need to be a role @mention, and you can just the roles name.")
        if mute_role not in user.roles:
            return await ctx.send(f"{user.display_name} is not muted")
        await user.remove_roles(mute_role)
        if user_id in self.config[guild_id]['mute_timers']:
            del self.config[guild_id]['mute_timers'][user_id]
            self.save_data()
        if guild_id in self.tasks and user_id in self.tasks[guild_id]:
            if not self.tasks[guild_id][user_id].done():
                self.tasks[guild_id][user_id].cancel()
            del self.tasks[guild_id][user_id]
            if not self.tasks[guild_id]:
                del self.tasks[guild_id]
        await ctx.send(f"Unmuted {user.name}")

    @commands.command(name='kick')
    @commands.cooldown(*utils.default_cooldown())
    @check_if_running()
    @has_required_permissions(kick_members=True)
    @commands.bot_has_permissions(embed_links=True, kick_members=True)
    async def kick(self, ctx, members: Greedy[discord.Member], *, reason="Unspecified"):
        if not members:
            return await ctx.send("You need to properly specify who to kick")
        e = discord.Embed(color=colors.fate())
        e.set_author(name=f"Kicking members", icon_url=ctx.author.avatar_url)
        msg = await ctx.send(embed=e)
        e.description = ""
        for i, member in enumerate(members):
            if member.top_role.position >= ctx.author.top_role.position:
                e.description += f"\n❌ {member} is Higher Than You"
            elif member.top_role.position >= ctx.guild.me.top_role.position:
                e.description += f"❌ {member} is Higher Than Me"
            else:
                await member.kick(reason=f"Kicked by {ctx.author} with ID: {ctx.author.id} for {reason}")
                e.description += f"✅ {member}"
            if i % 2 == 0 and i != len(members) - 1:
                await msg.edit(embed=e)
        await msg.edit(embed=e)

    @commands.command(name='ban')
    @commands.cooldown(2, 10, commands.BucketType.guild)
    @check_if_running()
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(embed_links=True, ban_members=True)
    async def ban(self, ctx, ids: Greedy[int], users: Greedy[discord.User], *, reason='Unspecified'):
        """ Ban cmd that supports more than just members """
        reason = f"{ctx.author}: {reason}"
        users_to_ban = len(ids if ids else []) + len(users if users else [])
        e = discord.Embed(color=colors.fate())
        if users_to_ban == 0:
            return await ctx.send("You need to specify who to ban")
        elif users_to_ban > 1:
            e.set_author(name=f"Banning {users_to_ban} user{'' if users_to_ban > 1 else ''}", icon_url=ctx.author.avatar_url)
        e.set_thumbnail(url='https://cdn.discordapp.com/attachments/514213558549217330/514345278669848597/8yx98C.gif')
        msg = await ctx.send(embed=e)
        for id in ids:
            member = ctx.guild.get_member(id)
            if isinstance(member, discord.Member):
                if member.top_role.position >= ctx.author.top_role.position:
                    e.add_field(name=f'◈ Failed to ban {member}', value="This users is above your paygrade", inline=False)
                    await msg.edit(embed=e)
                    continue
                elif member.top_role.position >= ctx.guild.me.top_role.position:
                    e.add_field(name=f'◈ Failed to ban {member}', value="I can't ban this user", inline=False)
                    await msg.edit(embed=e)
                    continue
            try:
                user = await self.bot.fetch_user(id)
            except:
                e.add_field(name=f'◈ Failed to ban {id}', value="That user doesn't exist", inline=False)
            else:
                await ctx.guild.ban(user, reason=reason)
                e.add_field(name=f'◈ Banned {user}', value=f'Reason: {reason}', inline=False)
            await msg.edit(embed=e)
        for user in users:
            member = discord.utils.get(ctx.guild.members, id=user.id)
            if member:
                if member.top_role.position >= ctx.author.top_role.position:
                    e.add_field(name=f'◈ Failed to ban {member}', value="This users is above your paygrade", inline=False)
                    await msg.edit(embed=e)
                    continue
                if member.top_role.position >= ctx.guild.me.top_role.position:
                    e.add_field(name=f'◈ Failed to ban {member}', value="I can't ban this user", inline=False)
                    await msg.edit(embed=e)
                    continue
            await ctx.guild.ban(user, reason=reason)
            e.add_field(name=f'◈ Banned {user}', value=f'Reason: {reason}', inline=False)
        if not e.fields:
            e.colour = colors.red()
            e.set_author(name="Couldn't ban any of the specified user(s)")
        await msg.edit(embed=e)

    @commands.command(name='unban')
    @commands.cooldown(*utils.default_cooldown())
    @check_if_running()
    @has_required_permissions(ban_members=True)
    @commands.bot_has_permissions(embed_links=True, ban_members=True, view_audit_log=True)
    async def unban(self, ctx, users: Greedy[discord.User], *, reason=':author:'):
        if not users:
            async for entry in ctx.guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
               users = entry.target,
        if len(users) == 1:
            user = users[0]
            await ctx.guild.unban(user, reason=reason.replace(':author:', str(ctx.author)))
            e = discord.Embed(color=colors.red())
            e.set_author(name=f'{user} unbanned', icon_url=user.avatar_url)
            await ctx.send(embed=e)
        else:
            e = discord.Embed(color=colors.green())
            e.set_author(name=f'Unbanning {len(users)} users', icon_url=ctx.author.avatar_url)
            e.description = ''
            msg = await ctx.send(embed=e)
            index = 1
            for user in users:
                e.description += f'✅ {user}'
                if index == 5:
                    await msg.edit(embed=e)
                    index = 1
                else:
                    index += 1
            await msg.edit(embed=e)

    @commands.command(name='mass-nick', aliases=['massnick'])
    @commands.cooldown(*utils.default_cooldown())
    @check_if_running()
    @has_required_permissions(manage_nicknames=True)
    @commands.bot_has_guild_permissions(manage_nicknames=True)
    async def mass_nick(self, ctx, *, nick=''):
        def gen_embed(iteration):
            e = discord.Embed(color=colors.fate())
            e.set_author(name="Mass Updating Nicknames", icon_url=ctx.author.avatar_url)
            e.description = f"{iteration + 1}/{len(members)} complete" \
                            f"\n1 role per 1.21 seconds" \
                            f"\nETA of {self.bot.utils.get_time(round((len(members) - (iteration + 1)) * 1.21))}"
            return e

        if len(nick) > 32:
            return await ctx.send("Nicknames cannot exceed 32 characters in length")
        members = [
            m for m in ctx.guild.members
            if m.top_role.position < ctx.author.top_role.position
               and m.top_role.position < ctx.guild.me.top_role.position
               and (m.nick if not nick else m.display_name != nick)
        ]
        if len(members) > 3600:
            async with ctx.typing():
                await asyncio.sleep(1)
            msg = await ctx.send("Bruh.. you get ONE hour, but that's it.", embed=gen_embed(0))
        else:
            msg = await ctx.send(embed=gen_embed(0))
        async with ctx.typing():
            react = await msg.add_reaction("❌")
            i = 0
            for i, member in enumerate(members[:3600]):
                for reaction in [r for r in msg.reactions if react is r]:
                    if reaction.count == 1:
                        continue
                    async for user in reaction.users():
                        if user.guild_permissions.manage_nicknames:
                            await msg.remove_reaction(reaction.emoji, user)
                            continue
                        return await msg.edit(content="Message Inactive: Operation Cancelled")
                if (i + 1) % 5 == 0:  # try checking the bots internal message cache instead
                    msg = await ctx.channel.fetch_message(msg.id)
                    await msg.edit(embed=gen_embed(i))
                try:
                    await member.edit(nick=nick)
                except discord.errors.Forbidden:
                    if not ctx.guild.me.guild_permissions.manage_nicknames:
                        await msg.edit(content="Message Inactive: Missing Permissions")
                        return await ctx.send("I'm missing permissions to manage nicknames. Canceling the operation :[")
                await asyncio.sleep(1.21)
                for reaction in msg.reactions:
                    if str(reaction.emoji) == "❌" and reaction.count > 1:
                        async for user in reaction.users():
                            if not user.guild_permissions.manage_nicknames:
                                await msg.remove_reaction(reaction.emoji, user)
                                continue
                            return await msg.edit(content="Message Inactive: Operation Cancelled")
            await msg.edit(content="Operation Complete", embed=gen_embed(i))

    @commands.command(name='mass-role', aliases=['massrole'])  # Have +/- support
    @commands.cooldown(*utils.default_cooldown())
    @check_if_running()
    @has_required_permissions(manage_roles=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    async def mass_role(self, ctx, *, role=None):
        def gen_embed(iteration):
            e = discord.Embed(color=colors.fate())
            e.set_author(name=f"Mass {action} Roles", icon_url=ctx.author.avatar_url)
            e.description = f"{iteration + 1}/{len(members)} complete" \
                            f"\n1 role per 1.21 seconds" \
                            f"\nETA of {self.bot.utils.get_time(round((len(members) - (iteration + 1)) * 1.21))}"

            return e

        if not role:
            e = discord.Embed(color=colors.fate())
            e.set_author(name="MassRole Usages", icon_url=ctx.author.avatar_url)
            e.description = f"Add, or remove roles from members in mass"
            p = self.bot.utils.get_prefix(ctx)
            e.add_field(
                name=f"{p}massrole @Role",
                value="Mass adds roles"
            )
            e.add_field(
                name=f"{p}massrole -@Role",
                value="Mass removes roles"
            )
            e.add_field(
                name="Note",
                value="@Role can be replaced with role names, role mentions, or role ids",
                inline=False
            )
            return await ctx.send(embed=e)

        role = role.lstrip("+")
        action = "Adding"
        i = 0
        if role.startswith("-"):
            action = "Removing"
            role = role.lstrip("-")
        role = await self.bot.utils.get_role(ctx, role)
        if not role:
            return
        members = [
            member for member in ctx.guild.members
            if member.top_role.position < ctx.author.top_role.position
               and member.top_role.position < ctx.guild.me.top_role.position
               and (role not in member.roles if action == "Adding"
                    else role in member.roles)
        ]
        if len(members) > 3600:
            async with ctx.typing():
                await asyncio.sleep(1)
            msg = await ctx.send("Bruh.. you get ONE hour, but that's it.", embed=gen_embed(0))
        else:
            msg = await ctx.send(embed=gen_embed(0))
        async with ctx.typing():
            react = await msg.add_reaction("❌")
            i = 0
            for i, member in enumerate(members[:3600]):
                for reaction in [r for r in msg.reactions if react is r]:
                    if reaction.count == 1:
                        continue
                    async for user in reaction.users():
                        if user.guild_permissions.manage_roles:
                            await msg.remove_reaction(reaction.emoji, user)
                            continue
                        return await msg.edit(content="Message Inactive: Operation Cancelled")
                if (i + 1) % 5 == 0:
                    msg = await ctx.channel.fetch_message(msg.id)
                    await msg.edit(embed=gen_embed(i))
                try:
                    if action == "Adding":
                        await member.add_roles(role)
                    else:
                        await member.remove_roles(role)
                except discord.errors.Forbidden:
                    if not ctx.guild.me.guild_permissions.manage_roles:
                        await msg.edit(content="Message Inactive: Missing Permissions")
                        return await ctx.send("I'm missing permissions to manage roles. Canceling the operation :[")
                await asyncio.sleep(1.21)
                for reaction in msg.reactions:
                    if str(reaction.emoji) == "❌" and reaction.count > 1:
                        async for user in reaction.users():
                            if not user.guild_permissions.manage_nicknames:
                                await msg.remove_reaction(reaction.emoji, user)
                                continue
                            return await msg.edit(content="Message Inactive: Operation Cancelled")
            await msg.edit(content="Operation Complete", embed=gen_embed(i))

    async def warn_user(self, channel, user, reason):
        guild = channel.guild
        guild_id = str(guild.id)
        user_id = str(user.id)
        if guild_id not in self.config:
            self.config[guild_id] = self.template
        warns = self.config[guild_id]["warns"]
        with open("./data/userdata/config.json", "r") as f:
            config = json.load(f)  # type: dict
        punishments = ['None', 'None', 'Mute', 'Kick', 'Softban', 'Ban']
        if guild_id in config['warns']['punishments']:
            punishments = config['warns']['punishments'][guild_id]
        if user_id not in warns:
            warns[user_id] = []
        if not isinstance(warns[user_id], list):
            warns[user_id] = []

        warns[user_id].append([reason, str(datetime.now())])
        total_warns = 0
        for reason, time in warns[user_id]:
            time = datetime.strptime(time, '%Y-%m-%d %H:%M:%S.%f')
            if (datetime.now() - time).days > 30:
                if guild_id in config['warns']['expire']:
                    warns[user_id].remove([reason, str(time)])
                    continue
            total_warns += 1
        self.save_data()

        if total_warns > len(punishments):
            punishment = punishments[-1:][0]
        else:
            punishment = punishments[total_warns - 1]
        if total_warns >= len(punishments):
            next_punishment = punishments[-1:][0]
        else:
            next_punishment = punishments[total_warns]

        e = discord.Embed(color=colors.fate())
        url = self.bot.user.avatar_url
        if user.avatar_url:
            url = user.avatar_url
        e.set_author(name=f'{user.name} has been warned', icon_url=url)
        e.description = f'**Warns:** [`{total_warns}`] '
        if punishment != 'None':
            e.description += f'**Punishment:** [`{punishment}`]'
        if punishment == 'None' and next_punishment != 'None':
            e.description += f'**Next Punishment:** [`{next_punishment}`]'
        else:
            if punishment == 'None' and next_punishment == 'None':
                e.description += f'**Reason:** [`{reason}`]'
            if next_punishment != 'None':
                e.description += f'\n**Next Punishment:** [`{next_punishment}`]'
        if punishment != 'None' and next_punishment != 'None':
            e.add_field(name='Reason', value=reason, inline=False)
        await channel.send(embed=e)
        try:
            await user.send(f"You've been warned in **{channel.guild}** for `{reason}`")
        except:
            pass
        if punishment == 'Mute':
            mute_role = None
            for role in channel.guild.roles:
                if role.name.lower() == "muted":
                    mute_role = role
            if not mute_role:
                bot = discord.utils.get(guild.members, id=self.bot.user.id)
                perms = list(perm for perm, value in bot.guild_permissions if value)
                if "manage_channels" not in perms:
                    return await channel.send("No muted role found, and I'm missing manage_channel permissions to set one up")
                mute_role = await guild.create_role(name="Muted", color=discord.Color(colors.black()))
                for channel in guild.text_channels:
                    await channel.set_permissions(mute_role, send_messages=False)
                for channel in guild.voice_channels:
                    await channel.set_permissions(mute_role, speak=False)
            if mute_role in user.roles:
                return await channel.send(f"{user.display_name} is already muted")
            user_roles = []
            for role in user.roles:
                try:
                    await user.remove_roles(role)
                    user_roles.append(role.id)
                    await asyncio.sleep(0.5)
                except:
                    pass
            await user.add_roles(mute_role)
            timer_info = {
                'action': 'mute',
                'channel': channel.id,
                'user': user.id,
                'end_time': str(datetime.now() + timedelta(seconds=7200)),
                'mute_role': mute_role.id,
                'roles': user_roles}
            if user_id not in self.config[guild_id]['timers']:
                self.config[guild_id]['timers'][user_id] = []
            self.config[guild_id]['timers'][user_id].append(timer_info)
            self.save_data()
            await asyncio.sleep(7200)
            if mute_role in user.roles:
                await user.remove_roles(mute_role)
                await channel.send(f"**Unmuted:** {user.name}")
            if user_id in self.config[guild_id]['timers'] and timer_info in self.config[guild_id]['timers'][user_id]:
                self.config[guild_id]['timers'][user_id].remove(timer_info)
            if not self.config[guild_id]['timers'][user_id]:
                del self.config[guild_id]['timers'][user_id]
            self.save_data()
        if punishment == 'Kick':
            try:
                await guild.kick(user, reason='Reached Sufficient Warns')
            except:
                await channel.send('Failed to kick this user')
        if punishment == 'Softban':
            try:
                await guild.kick(user, reason='Softban - Reached Sufficient Warns')
                await guild.unban(user, reason='Softban')
            except:
                await channel.send('Failed to softban this user')
        if punishment == 'Ban':
            try:
                await guild.ban(user, reason='Reached Sufficient Warns')
            except:
                await channel.send('Failed to ban this user')

    @commands.command(name='warn')
    @commands.cooldown(*utils.default_cooldown())
    @check_if_running()
    @has_warn_permission()
    async def warn(self, ctx, user: Greedy[discord.Member], *, reason):
        for user in list(user):
            if user.bot:
                await ctx.send(f"You can't warn {user.mention} because they're a bot")
                continue
            await self.warn_user(ctx.channel, user, reason)

    @commands.command(name='delwarn')
    @commands.cooldown(*utils.default_cooldown())
    @check_if_running()
    @has_warn_permission()
    @commands.bot_has_permissions(add_reactions=True)
    async def delwarn(self, ctx, user: Greedy[discord.Member], *, partial_reason):
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ['✔', '❌']

        guild_id = str(ctx.guild.id)
        for user in list(set(user)):
            user_id = str(user.id)
            if user_id not in self.config[guild_id]["warns"]:
                await ctx.send(f"{user} has no warns")
                continue
            for reason, warn_time in self.config[guild_id]["warns"][user_id]:
                if partial_reason in reason:
                    e = discord.Embed(color=colors.fate())
                    e.set_author(name="Is this the right warn?")
                    e.description = reason
                    msg = await ctx.send(embed=e)
                    await msg.add_reaction('✔')
                    await asyncio.sleep(0.5)
                    await msg.add_reaction('❌')
                    try:
                        reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
                    except asyncio.TimeoutError:
                        await msg.edit(content="Inactive Message: timed out due to no response")
                        if ctx.channel.permissions_for(ctx.guild.me).manage_messages:
                            await msg.clear_reactions()
                        return
                    else:
                        if str(reaction.emoji) == '✔':
                            self.config[guild_id]["warns"][user_id].remove([reason, warn_time])
                            self.save_data()
                            await ctx.message.delete()
                            await msg.delete()
                        else:
                            await msg.delete()
                        break

    @commands.command(name="clearwarns")
    @commands.cooldown(*utils.default_cooldown())
    @check_if_running()
    @has_warn_permission()
    async def clear_warns(self, ctx, user: Greedy[discord.Member]):
        guild_id = str(ctx.guild.id)
        for user in list(set(user)):
            user_id = str(user.id)
            if user_id not in self.config[guild_id]["warns"]:
                await ctx.send(f"{user} has no warns")
                continue
            if user.top_role.position >= ctx.author.top_role.position and ctx.author.id != ctx.guild.owner.id:
                await ctx.send(f"{user} is above your paygrade, take a seat")
            del self.config[guild_id]["warns"][user_id]
            await ctx.send(f"Cleared {user}'s warns")
            self.save_data()

    @commands.command(name="warns")
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def _warns(self, ctx, *, user=None):
        if not user:
            user = ctx.author
        else:
            user = utils.get_user(ctx, user)
        if not user:
            return await ctx.send('User not found')
        guild_id = str(ctx.guild.id)
        user_id = str(user.id)
        if user_id not in self.config[guild_id]["warns"]:
            self.config[guild_id]["warns"][user_id] = []
        warns = 0
        reasons = ''
        conf = self.bot.utils.get_config()
        for reason, time in self.config[guild_id]["warns"][user_id]:
            time = datetime.strptime(time, '%Y-%m-%d %H:%M:%S.%f')
            if (datetime.now() - time).days > 30:
                if guild_id in conf and 'expire' in conf[guild_id]["warns"] and conf[guild_id]["warns"]['expire'] == 'True':
                    self.config[guild_id]["warns"][user_id].remove([reason, time])
                    continue
            warns += 1
            reasons += f'\n• `{reason}`'
        e = discord.Embed(color=colors.fate())
        url = self.bot.user.avatar_url
        if user.avatar_url:
            url = user.avatar_url
        e.set_author(name=f'{user.name}\'s Warns', icon_url=url)
        e.description = f'**Total Warns:** [`{warns}`]' + reasons
        await ctx.send(embed=e)


def setup(bot):
    cls = Moderation(bot)
    globals()["cls"] = cls
    bot.add_cog(cls)
