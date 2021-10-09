"""
cogs.utility.anti_spam
~~~~~~~~~~~~~~~~~~~~~~~

A cog for automatically moderating multiple types of spam

:copyright: (C) 2020-present FrequencyX4
:license: Proprietary, see LICENSE for details
"""

import asyncio
from time import time
from datetime import datetime, timedelta, timezone
from contextlib import suppress
import traceback
import pytz
import re
from typing import *

from discord import ui, Interaction, SelectOption, TextChannel, Message
from discord.ext.commands import Context
import discord
from discord.errors import Forbidden, NotFound, HTTPException
from discord.ext import commands, tasks

from botutils import colors, get_time, emojis, get_prefixes_async, GetChoice
from botutils.interactions import AuthorView
from botutils.cache_rewrite import Cache
from classes.exceptions import IgnoredExit
from fate import Fate


utc = pytz.UTC
default_mentions = discord.AllowedMentions(users=True, roles=False, everyone=False)
abcs = "abcdefghijklmnopqrstuvwxyzجحخهعغفقثصضشسيبلاتتمكطدظزوةىرؤءذئأإآ"
defaults = {
    "rate_limit": [
        {
            "timespan": 3,
            "threshold": 4
        },
        {
            "timespan": 10,
            "threshold": 6
        }
    ],
    "mass_pings": {
        "per_message": 4,
        "ghost_pings": True,
        "thresholds": [{
            "timespan": 10,
            "threshold": 3
        },
        {
            "timespan": 30,
            "threshold": 6
        }
        ]
    },
    "duplicates": {
        "per_message": 10,
        "same_link": 25,
        "same_image": 25,
        "sticker": 10,
        "same_sticker": 60,
        "max_open_threads": 1,
        "thresholds": [{
            "timespan": 25,
            "threshold": 4
        }]
    },
    "inhuman": {
        "non_abc": True,
        "tall_messages": True,
        "empty_lines": True,
        "unknown_chars": True,
        "ascii": True,
        "copy_paste": True
    }
}

thresholds = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 20, 25]
timespans = [3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20, 25, 30, 45, 60, 120, 240]
per_each_timespans = ["None (Disable)", 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 25, 35, 45, 60, 120]


class AntiSpam(commands.Cog):
    spam_cd: Dict[int, Dict[str, Dict[int, List[int]]]] = {}   # Cooldown cache for rate limiting
    macro_cd: Dict[int, List[Union[float, List[float]]]] = {}  # Per-user message interval cache to look for patterns
    dupes: Dict[str, List[Optional[discord.Message]]] = {}     # Per-channel index to keep track of duplicate messages
    msgs: Dict[int, List[Optional[discord.Message]]] = {}      # Limited message cache
    mutes: Dict[int, Dict[int, List[float]]] = {}              # Keep track of mutes to increment the timer per-mute
    typing: Dict[int, datetime.now] = {}                       # Keep track of typing to prevent large copy-pastes
    urls: Dict[int, List[str]] = {}                            # Cache sent urls to prevent repeats
    imgs: Dict[int, List[int]] = {}                            # Cache sent images to prevent repeats
    r_cache = {}

    def __init__(self, bot: Fate) -> None:
        if "antispam_mutes" not in bot.tasks:
            bot.tasks["antispam_mutes"] = {}
        self.bot = bot
        self.config = Cache(bot, "AntiSpam")
        self.cache_cleanup_task.start()

    def cog_unload(self) -> None:
        self.cache_cleanup_task.cancel()
        self.config.task.cancel()

    async def cog_before_invoke(self, ctx):
        await self.config.cache(ctx.guild.id)

    async def is_enabled(self, guild_id) -> bool:
        """ Denotes if a server has the module enabled """
        await self.config.cache(guild_id)
        return guild_id in self.config

    async def get_mutes(self) -> dict:
        """ Fetches the incomplete mutes from the db """
        mutes = {}
        async with self.bot.utils.cursor() as cur:
            await cur.execute(
                f"select guild_id, channel_id, user_id, mute_role_id, end_time "
                f"from anti_spam_mutes;"
            )
            results = await cur.fetchall()
            for guild_id, channel_id, user_id, mute_role_id, end_time in results:
                if guild_id not in mutes:
                    mutes[guild_id] = {}
                mutes[guild_id][user_id] = {
                    "channel_id": channel_id,
                    "mute_role_id": mute_role_id,
                    "end_time": end_time
                }
        return mutes

    async def destroy_task(self, guild_id, user_id) -> None:
        """ Clean up the cache before ending a mute task """
        guild_id = int(guild_id)
        user_id = int(user_id)
        if guild_id in self.bot.tasks["antispam_mutes"]:
            if user_id in self.bot.tasks["antispam_mutes"][guild_id]:
                del self.bot.tasks["antispam_mutes"][guild_id][user_id]
            if not self.bot.tasks["antispam_mutes"][guild_id]:
                del self.bot.tasks["antispam_mutes"][guild_id]
        with suppress(AttributeError):
            async with self.bot.utils.cursor() as cur:
                await cur.execute(
                    f"delete from anti_spam_mutes "
                    f"where guild_id = {guild_id} "
                    f"and user_id = {user_id};"
                )

    @staticmethod
    async def cleanup_from_message(msg) -> None:
        """ Remove duplicate messages if duplicate message spam was detected """
        async for m in msg.channel.history(limit=10):
            if m.content == msg.content:
                with suppress(NotFound, Forbidden):
                    await m.delete()

    @tasks.loop(seconds=10)
    async def cache_cleanup_task(self) -> None:
        # Timer cache
        for guild_id, timers in list(self.bot.tasks["antispam_mutes"].items()):
            await asyncio.sleep(0)
            if not timers and guild_id in self.bot.tasks["antispam_mutes"]:
                del self.bot.tasks["antispam_mutes"][guild_id]

        # Message Index
        for user_id, messages in list(self.msgs.items()):
            await asyncio.sleep(0)
            for msg in messages:
                with suppress(KeyError, IndexError, ValueError):
                    if not msg:
                        self.msgs[user_id].remove(msg)
                        continue
                    elif msg.created_at < datetime.now(tz=timezone.utc) - timedelta(seconds=240):
                        self.msgs[user_id].remove(msg)
            with suppress(KeyError):
                if not self.msgs[user_id]:
                    del self.msgs[user_id]

        # Duplicate text index
        for channel_id, messages in list(self.dupes.items()):
            await asyncio.sleep(0)
            for message in messages:
                with suppress(KeyError, ValueError, IndexError):
                    if not message:
                        self.dupes[channel_id].remove(message)
                    elif message.created_at < datetime.now(tz=timezone.utc) - timedelta(minutes=45):
                        self.dupes[channel_id].remove(message)
            with suppress(KeyError):
                if not self.dupes[channel_id]:
                    del self.dupes[channel_id]

        # Typing timestamps
        for user_id, timestamps in list(self.typing.items()):
            await asyncio.sleep(0)
            if not any((datetime.now(tz=timezone.utc) - date).seconds < 60 for date in self.typing[user_id]):
                if user_id in self.typing:
                    del self.typing[user_id]

    @commands.group(name="anti-spam", aliases=["antispam"], description="Shows info on how to use each command")
    @commands.cooldown(1, 2, commands.BucketType.user)
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def anti_spam(self, ctx):
        if not ctx.invoked_subcommand and 'help' not in ctx.message.content:
            e = discord.Embed(color=colors.fate)
            e.set_author(name='AntiSpam Usage', icon_url=ctx.author.display_avatar.url)
            if ctx.guild.icon:
                e.set_thumbnail(url=ctx.guild.icon.url)
            e.description = '**.anti-spam enable**\n`• enables all anti-spam modules`\n' \
                            '**.anti-spam enable module**\n`• enables a single module`\n' \
                            '**.anti-spam disable**\n`• disables all anti-spam modules`\n' \
                            '**.anti-spam disable module**\n`• disables a single module`\n' \
                            '**.anti-spam alter-sensitivity**\n`• alters anti-spam sensitivity`\n' \
                            '**.anti-spam ignore #channel**\n`• ignores spam in a channel`\n' \
                            '**.anti-spam unignore #channel**\n`• no longer ignores a channels spam`'
            modules = '**Rate-Limit:** `sending msgs fast`\n' \
                      '**Mass-Pings:** `mass mentioning users`\n' \
                      '**Anti-Macro:** `using macros for bots`\n' \
                      '**Duplicates:** `copying and pasting`\n' \
                      '**Inhuman:** `abnormal, ascii, tall, etc`'
            e.add_field(name="◈ Modules", value=modules, inline=False)
            guild_id = ctx.guild.id
            if guild_id in self.config:
                conf = ""
                for key in self.config[guild_id].keys():
                    if key != "ignored":
                        conf += f"**{key.replace('_', '-')}:** `enabled`\n"
                if "ignored" in self.config[guild_id]:
                    channels = []
                    for channel_id in self.config[guild_id]["ignored"]:
                        channel = self.bot.get_channel(channel_id)
                        if channel and channel.guild.id == ctx.guild.id:
                            channels.append(channel)
                        else:
                            self.config[guild_id]["ignored"].remove(channel_id)
                    if channels:
                        conf += "**Ignored:** " + ", ".join(c.mention for c in channels)
                if conf:
                    e.add_field(name="◈ Config", value=conf, inline=False)
            await ctx.send(embed=e)

    @anti_spam.command(name="configure", aliases=["config"], description="Interactively configure antispam")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(embed_links=True, add_reactions=True, manage_messages=True)
    async def _configure(self, ctx):
        if ctx.guild.id not in self.config:
            return await ctx.send(
                f"AntiSpam isn't enabled. You can enable it via {ctx.prefix}antispam enable"
            )

        # Parse the choices
        choices = list(self.config[ctx.guild.id].keys())
        if "ignored" in choices:
            choices.remove("ignored")

        # Fetch the choice
        choice_view = GetChoice(ctx, choices, delete_after=False)
        choice = await choice_view

        # Run the configure view
        config_view = ConfigureMenu(ctx, choice)
        await choice_view.message.edit(view=config_view)

        # Remove the view from the original message when done
        await config_view.wait()
        e = discord.Embed(color=colors.red)
        e.set_author(name="Expired Menu", icon_url=ctx.author.display_avatar.url)
        await choice_view.message.edit(content=None, view=None, embed=e)

    @anti_spam.group(name="enable", description="Enables the default configuration")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True, manage_roles=True, manage_channels=True)
    async def _enable(self, ctx):
        if not ctx.invoked_subcommand:
            guild_id = ctx.guild.id
            if guild_id in self.config:
                return await ctx.send("Anti spam is already enabled")
            self.config[guild_id] = defaults
            await self.config.flush()
            await ctx.send("Enabled the default anti-spam config")

    @_enable.command(name="rate-limit", description="Limits users to x messages within x seconds")
    @commands.has_permissions(manage_messages=True)
    async def _enable_rate_limit(self, ctx):
        guild_id = ctx.guild.id
        if guild_id not in self.config:
            self.config[guild_id] = {}
        self.config[guild_id]["rate_limit"] = defaults["rate_limit"]
        await self.config.flush()
        await ctx.send("Enabled the rate-limit module")

    @_enable.command(name="mass-pings", aliases=["mass-ping"], description="Flags when a user pings too much")
    @commands.has_permissions(manage_messages=True)
    async def _enable_mass_pings(self, ctx):
        guild_id = ctx.guild.id
        if guild_id not in self.config:
            self.config[guild_id] = {}
        self.config[guild_id]["mass_pings"] = defaults["mass_pings"]
        await self.config.flush()
        await ctx.send("Enabled the rate-limit module")

    @_enable.command(name='anti-macro', description="Flags using autoclickers or macros to spam or exploit bots")
    @commands.has_permissions(manage_messages=True)
    async def _enable_anti_macro(self, ctx):
        guild_id = ctx.guild.id
        if guild_id not in self.config:
            self.config[guild_id] = {}
        if "anti_macro" in self.config[guild_id]:
            return await ctx.send("Anti macro is already enabled")
        self.config[guild_id]["anti_macro"] = {}
        await self.config.flush()
        await ctx.send("Enabled the anti-macro module")

    @_enable.command(name="duplicates", description="Flag duplicate content like links, images, and stickers")
    @commands.has_permissions(manage_messages=True)
    async def _enable_duplicates(self, ctx):
        guild_id = ctx.guild.id
        if guild_id not in self.config:
            self.config[guild_id] = {}
        self.config[guild_id]["duplicates"] = defaults["duplicates"]
        await self.config.flush()
        await ctx.send("Enabled the duplicates module")

    @_enable.command(name="inhuman", description="Flags abnormal text like tall messages, ascii, and copy pasting bulky messages")
    @commands.has_permissions(manage_messages=True)
    async def _enable_inhuman(self, ctx):
        guild_id = ctx.guild.id
        if guild_id not in self.config:
            self.config[guild_id] = {}
        self.config[guild_id]["inhuman"] = defaults["inhuman"]
        await self.config.flush()
        await ctx.send("Enabled the inhuman module")

    @anti_spam.group(name="disable", description="Disables antispam all-together")
    @commands.has_permissions(manage_messages=True)
    async def _disable(self, ctx):
        if not ctx.invoked_subcommand:
            guild_id = ctx.guild.id
            if guild_id not in self.config:
                return await ctx.send("Anti-Spam isn't enabled")
            self.config.remove(guild_id)
            await ctx.send("Disabled anti-spam")

    @_disable.command(name="rate-limit", aliases=["ratelimit"], description="Disables the rate-limit module")
    @commands.has_permissions(manage_messages=True)
    async def _disable_rate_limit(self, ctx):
        guild_id = ctx.guild.id
        if guild_id not in self.config:
            return await ctx.send("Anti spam isn't enabled")
        if "rate_limit" not in self.config[guild_id]:
            return await ctx.send("Rate limit isn't enabled")
        self.config.remove_sub(guild_id, "rate_limit")
        await ctx.send("Disabled the rate-limit module")

    @_disable.command(name="anti-macro", aliases=["antimacro"], description="Disables the anti-macro module")
    @commands.has_permissions(manage_messages=True)
    async def _disable_anti_macro(self, ctx):
        guild_id = ctx.guild.id
        if guild_id not in self.config:
            return await ctx.send("Anti spam isn't enabled")
        if "anti_macro" not in self.config[guild_id]:
            return await ctx.send("Anti Macro isn't enabled")
        self.config.remove_sub(guild_id, "anti_macro")
        await ctx.send("Disabled the anti-macro module")

    @_disable.command(name="mass-pings", aliases=["masspings"], description="Disables the mass-pings module")
    @commands.has_permissions(manage_messages=True)
    async def _disable_mass_pings(self, ctx):
        guild_id = ctx.guild.id
        if guild_id not in self.config:
            return await ctx.send("Anti spam isn't enabled")
        if "mass_pings" not in self.config[guild_id]:
            return await ctx.send("Mass pings isn't enabled")
        self.config.remove_sub(guild_id, "mass_pings")
        await ctx.send("Disabled the mass-pings module")

    @_disable.command(name="duplicates", aliases=["duplicate"], description="Disables the duplicates module")
    @commands.has_permissions(manage_messages=True)
    async def _disable_duplicates(self, ctx):
        guild_id = ctx.guild.id
        if guild_id not in self.config:
            return await ctx.send("Anti spam isn't enabled")
        if "duplicates" not in self.config[guild_id]:
            return await ctx.send("Duplicates isn't enabled")
        self.config.remove_sub(guild_id, "rate_limit")
        await ctx.send("Disabled the duplicates module")

    @_disable.command(name="inhuman", description="Disables the inhuman module")
    @commands.has_permissions(manage_messages=True)
    async def _disable_inhuman(self, ctx):
        guild_id = ctx.guild.id
        if guild_id not in self.config:
            return await ctx.send("Anti spam isn't enabled")
        if "inhuman" not in self.config[guild_id]:
            return await ctx.send("Inhuman isn't enabled")
        self.config.remove_sub(guild_id, "inhuman")
        await ctx.send("Disabled the inhuman module")

    @anti_spam.command(name="ignore", description="Has antispam ignore a specific channel")
    @commands.has_permissions(manage_messages=True)
    async def _ignore(self, ctx, *channel_mentions: discord.TextChannel):
        guild_id = ctx.guild.id
        if guild_id not in self.config:
            return await ctx.send("Anti spam isn't enabled")
        if "ignored" not in self.config[guild_id]:
            self.config[guild_id]["ignored"] = []
        for channel in channel_mentions[:5]:
            if "ignored" in self.config[guild_id]:
                if channel.id in self.config[guild_id]["ignored"]:
                    await ctx.send(f"{channel.mention} is already ignored")
                    continue
            if "ignored" not in self.config[guild_id]:
                self.config[guild_id]["ignored"] = []
            self.config[guild_id]["ignored"].append(channel.id)
            await ctx.send(f"I'll now ignore {channel.mention}")
        await self.config.flush()

    @anti_spam.command(name="unignore", description="Disable ignoring a specific channel")
    @commands.has_permissions(manage_messages=True)
    async def _unignore(self, ctx, *channel_mentions: discord.TextChannel):
        guild_id = ctx.guild.id
        if guild_id not in self.config:
            return await ctx.send("Anti spam isn't enabled")
        if "ignored" not in self.config[guild_id]:
            return await ctx.send("There aren't any ignored channels")
        for channel in channel_mentions[:5]:
            if channel.id not in self.config[guild_id]["ignored"]:
                await ctx.send(f"{channel.mention} isn't ignored")
                continue
            self.config[guild_id]["ignored"].remove(channel.id)
            if not self.config[guild_id]["ignored"]:
                self.config.remove_sub(guild_id, "ignored")
            await ctx.send(f"I'll no longer ignore {channel.mention}")
        await self.config.flush()

    @anti_spam.command(name="stats")
    @commands.is_owner()
    async def stats(self, ctx):
        running = 0
        muted = 0
        done = []
        for guild_id, timers in self.bot.tasks["antispam_mutes"].items():
            for user_id, task in timers.items():
                if task.done():
                    done.append(task)
                    guild = self.bot.get_guild(int(guild_id))
                    if guild:
                        mute_role = await self.bot.attrs.get_mute_role(guild)
                        user = guild.get_member(int(user_id))
                        if user and mute_role and mute_role in user.roles:
                            muted += 1
                else:
                    running += 1
        e = discord.Embed(color=self.bot.config["theme_color"])
        e.set_author(name="AntiSpam Stats", icon_url=self.bot.user.display_avatar.url)
        emotes = emojis
        errored = []
        try:
            errored = [task for task in done if task.exception() or task.result()]
        except:
            e.add_field(
                name="◈ Error",
                value=traceback.format_exc(),
                inline=False
            )
        e.description = f"{emotes.online} {running} tasks running\n" \
                        f"{emotes.idle} {len(done) - len(errored)} tasks done\n" \
                        f"{emotes.dnd} {len(errored)} tasks errored\n" \
                        f"{emotes.offline} {muted} still muted"
        await ctx.send(embed=e)

    async def cache_link(self, channel: TextChannel, match: str) -> None:
        """ Cache a url for x seconds to prevent it being resent """
        self.urls[channel.id].append(match)
        duration = self.config[channel.guild.id]["duplicates"]["same_link"]
        await asyncio.sleep(duration)
        with suppress(ValueError):
            self.urls[channel.id].remove(match)
        if not self.urls[channel.id]:
            del self.urls[channel.id]

    async def cache_image(self, channel: TextChannel, size: int) -> None:
        """ Cache image properties for x seconds to prevent it being resent """
        self.imgs[channel.id].append(size)
        duration = self.config[channel.guild.id]["duplicates"]["same_image"]
        await asyncio.sleep(duration)
        with suppress(ValueError):
            self.imgs[channel.id].remove(size)
        if not self.imgs[channel.id]:
            del self.imgs[channel.id]

    async def has_pattern(self, intervals: List[int]) -> bool:
        """ Looks for repeating intervals """
        total = []
        for index in range(len(intervals)):
            for i in range(5):
                await asyncio.sleep(0)
                total.append(intervals[index:index + i])

        total = [p for p in total if len(p) > 2]
        top = []
        for lst in sorted(total, key=lambda v: total.count(v), reverse=True):
            await asyncio.sleep(0)
            dat = [lst, total.count(lst)]
            if dat not in top:
                top.append(dat)

        for lst, count in top[:5]:
            await asyncio.sleep(0)
            div = round(len(intervals) / len(lst))
            if all(i < 3 for i in lst):
                return False
            elif count >= div - 1:
                return True
            else:
                return False

    def has_abnormal(self, content: str) -> bool:
        """ Checks if the message content has any mostly non abc words """
        for word in content.split():
            if len(word) < 6 or word.isdigit():
                continue
            if any(word.endswith(char) for char in [".", "!", "?"]):
                continue
            if "@" in word or "<:" in word or "<a:" in word:
                continue
            total_abc = len([c for c in word if c.lower() in abcs])
            non_abc = len(word) - total_abc
            if not non_abc:
                continue
            if not total_abc or non_abc / total_abc * 100 > 60:
                return True
        return False

    @commands.Cog.listener()
    async def on_typing(self, channel, user, when):
        """ Log typing timestamps for the copy_paste module """
        await self.config.cache(channel.guild.id)
        if hasattr(channel, "guild") and channel.guild and channel.guild.id in self.config:
            guild_id = channel.guild.id
            if "inhuman" in self.config[guild_id] and self.config[guild_id]["inhuman"]["copy_paste"]:
                user_id = user.id
                if user_id not in self.typing:
                    self.typing[user_id] = []
                self.typing[user_id].append(when)

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if not isinstance(msg.guild, discord.Guild) or msg.author.bot:
            return
        guild_id = msg.guild.id
        await self.config.cache(guild_id)
        if guild_id in self.config and self.config[guild_id]:
            conf: dict = self.config[guild_id]
            if "ignored" in conf and msg.channel.id in conf["ignored"]:
                return

            if not msg.guild.me or not msg.channel:
                return
            perms = msg.channel.permissions_for(msg.guild.me)
            if not perms.manage_messages or not perms.manage_roles:
                return
            await asyncio.sleep(0.21)

            users = [msg.author]
            reason = "Unknown"
            user_id = msg.author.id
            triggered = False

            # msgs to delete if triggered
            if user_id not in self.msgs:
                self.msgs[user_id] = []
            self.msgs[user_id].append(msg)
            self.msgs[user_id] = self.msgs[user_id][-15:]

            # Inhuman checks
            if "inhuman" in conf and msg.content:
                content = str(msg.content).lower()
                lines = content.split("\n")

                total_abcs = len([c for c in content if c in abcs])
                total_abcs = total_abcs if total_abcs else 1

                total_spaces = content.count(" ")
                total_spaces = total_spaces if total_spaces else 1

                has_abcs = any(content.count(c) for c in abcs)

                # non abc char spam
                if conf["inhuman"]["non_abc"]:
                    if len(msg.content) > 256 and not has_abcs:
                        reason = "Inhuman: non abc"
                        triggered = True

                # Tall msg spam
                if conf["inhuman"]["tall_messages"]:
                    if len(content.split("\n")) > 8 and sum(len(line) for line in lines if line) < 21:
                        reason = "Inhuman: tall message"
                        triggered = True
                    elif len(content.split("\n")) > 5 and not has_abcs:
                        reason = "Inhuman: tall message"
                        triggered = True

                # Empty lines spam
                if conf["inhuman"]["empty_lines"]:
                    small_lines = len([l for l in lines if not l or len(l) < 3])
                    large_lines = len([l for l in lines if l and len(l) > 2])
                    if small_lines > large_lines and len(lines) > 8:
                        reason = "Inhuman: too many empty lines"
                        triggered = True

                # Mostly unknown chars spam
                if conf["inhuman"]["unknown_chars"]:
                    lmt = 128
                    if ":" in content:
                        lmt = 256
                    if len(content) > lmt and len(content) / total_abcs > 3:
                        if not ("http" in content and len(content) < 512):
                            reason = "Inhuman: mostly non abc characters"
                            triggered = True

                # ASCII / Spammed chars
                if conf["inhuman"]["ascii"]:
                    if len(content) > 256 and len(content) / total_spaces > 10:
                        reason = "Inhuman: ascii"
                        triggered = True

                # Pasting large messages without typing much, or at all
                lmt = 250 if "http" in msg.content else 100
                check = msg.channel.permissions_for(msg.author).manage_messages
                if not check and conf["inhuman"]["copy_paste"] and len(msg.content) > lmt:
                    if user_id not in self.typing:
                        reason = "pasting bulky message (check #1)"
                        triggered = None
                    elif len(msg.content) > 150:
                        typed_recently = any(
                            (datetime.now(tz=timezone.utc) - date).seconds < 35 for date in self.typing[user_id]
                        )
                        if not typed_recently:
                            reason = "pasting bulky message (check #2)"
                            triggered = None
                        if len(msg.content) > 750:
                            count = len([
                                ts for ts in self.typing[user_id]
                                if (datetime.now(tz=timezone.utc) - ts).seconds < 60
                            ])
                            if count < 2:
                                reason = "pasting bulky message (check #3)"
                                triggered = None
                    if user_id in self.typing:
                        del self.typing[user_id]

                if msg.guild.id in [850956124168519700, 397415086295089155] and len(msg.content) > 15:
                    lmt_dt = datetime.now(tz=timezone.utc) - timedelta(seconds=15)
                    if self.has_abnormal(msg.content):
                        for m in self.msgs[user_id]:
                            await asyncio.sleep(0)
                            if m.id != msg.id and self.has_abnormal(m.content) and m.created_at > lmt_dt:
                                reason = "Abnormal duplicate"
                                triggered = True

            with suppress(KeyError):

                # Rate limit
                if "rate_limit" in conf and conf["rate_limit"]:
                    await asyncio.sleep(0)
                    if guild_id not in self.spam_cd:
                        self.spam_cd[guild_id] = {}
                    for rate_limit in list(conf["rate_limit"]):
                        await asyncio.sleep(0)
                        dat = [
                            *list(rate_limit.values()),
                            ",".join(str(v) for v in rate_limit.values())
                        ]
                        timespan, threshold, uid = dat
                        if uid not in self.spam_cd[guild_id]:
                            self.spam_cd[guild_id][uid] = {}
                    for rl_id in list(self.spam_cd[guild_id].keys()):
                        await asyncio.sleep(0)
                        raw = rl_id.split(",")
                        dat = {
                            "timespan": int(raw[0]),
                            "threshold": int(raw[1])
                        }
                        if dat not in conf["rate_limit"]:
                            del self.spam_cd[guild_id][rl_id]

                    for rl_id in list(self.spam_cd[guild_id].keys()):
                        await asyncio.sleep(0)
                        timeframe, threshold = rl_id.split(",")
                        now = int(time() / int(timeframe))
                        if user_id not in self.spam_cd[guild_id][rl_id]:
                            self.spam_cd[guild_id][rl_id][user_id] = [now, 0]
                        if self.spam_cd[guild_id][rl_id][user_id][0] == now:
                            self.spam_cd[guild_id][rl_id][user_id][1] += 1
                        else:
                            self.spam_cd[guild_id][rl_id][user_id] = [now, 0]
                        if self.spam_cd[guild_id][rl_id][user_id][1] >= int(threshold):
                            reason = f"{threshold} messages within {timeframe} seconds"
                            triggered = True

                # mass pings
                if "mass_pings" in conf and conf["mass_pings"]["per_message"]:
                    await asyncio.sleep(0)
                    pings = [msg.raw_mentions, msg.raw_role_mentions]
                    total_pings = sum(len(group) for group in pings)  # type: ignore
                    if total_pings > conf["mass_pings"]["per_message"]:
                        if msg.guild.id not in self.bot.filtered_messages:
                            self.bot.filtered_messages[msg.guild.id] = {}
                        self.bot.filtered_messages[msg.guild.id][msg.id] = time()
                        reason = "mass pinging"
                        triggered = True

                    if user_id not in self.msgs:
                        self.msgs[user_id] = []
                    pongs = lambda s: [
                        m for m in self.msgs[user_id]
                        if m and m.created_at > datetime.now(tz=timezone.utc) - timedelta(seconds=s)
                           and sum(len(group) for group in [
                            m.mentions, m.raw_mentions, m.role_mentions, m.raw_role_mentions
                        ])
                    ]

                    for threshold in conf["mass_pings"]["thresholds"]:
                        await asyncio.sleep(0)
                        if user_id not in self.msgs:
                            self.msgs[user_id] = []
                        if len(pongs(threshold["timespan"])) > threshold["threshold"]:
                            if msg.guild.id not in self.bot.filtered_messages:
                                self.bot.filtered_messages[msg.guild.id] = {}
                            self.bot.filtered_messages[msg.guild.id][msg.id] = time()
                            reason = "mass pinging"
                            triggered = True

                # anti macro
                if "anti_macro" in conf:
                    await asyncio.sleep(0)
                    ts = datetime.timestamp
                    if user_id not in self.macro_cd:
                        self.macro_cd[user_id] = [ts(msg.created_at), []]
                    else:
                        self.macro_cd[user_id][1] = [
                            *self.macro_cd[user_id][1][-20:],
                            ts(msg.created_at) - self.macro_cd[user_id][0]
                        ]
                        self.macro_cd[user_id][0] = ts(msg.created_at)
                        intervals = [int(i) for i in self.macro_cd[user_id][1]]
                        if len(intervals) > 12:
                            if all(round(cd) == round(intervals[0]) for cd in intervals):
                                if intervals[0] > 3 and intervals[0] < 3:
                                    triggered = True
                                    reason = "Repeated messages at the same interval"
                            elif await self.has_pattern(intervals):
                                triggered = True
                                reason = "Using a bot/macro"

                # duplicate messages
                if "duplicates" in conf:
                    await asyncio.sleep(0)
                    word = msg.content.split()[0]
                    if len(self.msgs[user_id]) > 3 and word.lower() != word.upper():
                        if all(m.content.startswith(word) for m in self.msgs[user_id][-4:]):
                            triggered = True
                            reason = "Duplicate messages"
                    if msg.guild.me and msg.channel.permissions_for(msg.guild.me).read_message_history and msg.content:
                        with self.bot.utils.operation_lock(key=msg.id):
                            channel_id = str(msg.channel.id)
                            if channel_id not in self.dupes:
                                self.dupes[channel_id] = []
                            self.dupes[channel_id] = [
                                msg, *[
                                    msg for msg in self.dupes[channel_id]
                                    if msg.created_at > datetime.now(tz=timezone.utc) - timedelta(seconds=60)
                                ]
                            ]
                            for threshold in conf["duplicates"]["thresholds"]:
                                lmt = threshold["threshold"]
                                timeframe = threshold["timespan"]
                                for message in list(self.dupes[channel_id]):
                                    await asyncio.sleep(0)
                                    if channel_id not in self.dupes:
                                        break
                                    dupes = [
                                        m for m in self.dupes[channel_id]
                                        if m and m.content and m.content == message.content
                                           and m.created_at > datetime.now(tz=timezone.utc) - timedelta(seconds=timeframe)
                                           and len(m.content) > 5
                                    ]
                                    all_are_single_use = all(
                                        len([m for m in dupes if m.author.id == dupes[i].author.id]) == 1
                                        for i in range(len(dupes))
                                    )
                                    if len(dupes) > 1 and not all_are_single_use:
                                        if len([d for d in dupes if d.author.id == dupes[0].author.id]) == 1:
                                            dupes.pop(0)
                                    if len(dupes) > lmt:
                                        history = await msg.channel.history(limit=2).flatten()
                                        if not any(m.author.bot for m in history):
                                            users = set(list([
                                                *[m.author for m in dupes if m], *users
                                            ]))
                                            for message in dupes:
                                                with suppress(IndexError, ValueError, KeyError):
                                                    self.dupes[channel_id].remove(message)
                                            with suppress(Forbidden, NotFound):
                                                await msg.channel.delete_messages([
                                                    message for message in dupes if message
                                                ])
                                            reason = f"Duplicates: {lmt} duplicates within {timeframe} seconds"
                                            triggered = True
                                            break
                                if triggered:
                                    break

                    if conf["duplicates"]["same_link"]:
                        await asyncio.sleep(0)
                        if "http" in msg.content or "discord.gg" in msg.content:
                            search = lambda: re.search("((https?://)|(www\.)|(discord\.gg/))[a-zA-Z0-9./-_?]+", msg.content)
                            if r := await self.bot.loop.run_in_executor(None, search):
                                if msg.channel.id not in self.urls:
                                    self.urls[msg.channel.id]: List[str] = []
                                re_match: str = r.group()
                                if re_match in self.urls[msg.channel.id]:
                                    reason = "Duplicates: Repeated link"
                                    triggered = True
                                self.bot.loop.create_task(self.cache_link(msg.channel, re_match))

                    if conf["duplicates"]["same_image"] and msg.attachments:
                        for attachment in msg.attachments:
                            await asyncio.sleep(0)
                            if msg.channel.id not in self.imgs:
                                self.imgs[msg.channel.id] = []
                            size = attachment.size
                            if size in self.imgs[msg.channel.id]:
                                reason = "Duplicates: Repeated image"
                                triggered = True
                            self.bot.loop.create_task(self.cache_image(msg.channel, size))

                    if msg.stickers and conf["duplicates"]["same_sticker"]:
                        stickers_sent = []
                        lmt: int = conf["duplicates"]["same_sticker"]
                        lmt_dt = datetime.now(tz=timezone.utc) - timedelta(seconds=lmt)
                        for m in self.msgs[user_id]:
                            if m.id == msg.id:
                                continue
                            if m.created_at > lmt_dt:
                                for sticker in m.stickers:
                                    if sticker.id in stickers_sent:
                                        triggered = True
                                        reason = f"Duplicate sticker within {lmt} seconds"
                                        break
                                    stickers_sent.append(sticker.id)

                    if msg.stickers and conf["duplicates"]["sticker"]:
                        lmt: int = conf["duplicates"]["sticker"]
                        lmt_dt = datetime.now(tz=timezone.utc) - timedelta(seconds=lmt)
                        for m in self.msgs[user_id]:
                            if m.id == msg.id:
                                continue
                            if m.stickers and m.created_at > lmt_dt:
                                triggered = True
                                reason = f"Sending more than 1 sticker within {lmt} seconds"
                                break

                if (triggered is None or "ascii" in reason) and not msg.author.guild_permissions.administrator:
                    if msg.guild.id not in self.bot.filtered_messages:
                        self.bot.filtered_messages[msg.guild.id] = {}
                    self.bot.filtered_messages[msg.guild.id][msg.id] = time()
                    with suppress(HTTPException, NotFound, Forbidden):
                        await msg.delete()
                        e = discord.Embed(color=self.bot.config["theme_color"])
                        e.description = f"{msg.author.mention} no {reason}"
                        await msg.channel.send(
                            embed=e,
                            delete_after=5,
                            allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False)
                        )
                    return

                if triggered and guild_id in self.config:
                    # Mute the relevant users
                    for iteration, user in enumerate(list(set(users))):
                        if not isinstance(user, discord.Member):
                            continue
                        with self.bot.utils.operation_lock(key=user.id):
                            guild_id = msg.guild.id
                            user_id = user.id
                            bot_user = msg.guild.me
                            if not bot_user:
                                return
                            perms = msg.channel.permissions_for(bot_user)
                            if not perms.manage_messages:
                                return

                            # Purge away spam
                            messages = []
                            if user_id in self.msgs:
                                messages = [
                                    m for m in self.msgs[user_id]
                                    if m and m.created_at > datetime.now(tz=timezone.utc) - timedelta(seconds=15)
                                ]
                            self.msgs[user_id] = []  # Remove soon to be deleted messages from the list
                            for m in messages:
                                if m.guild.id not in self.bot.filtered_messages:
                                    self.bot.filtered_messages[m.guild.id] = {}
                                self.bot.filtered_messages[m.guild.id][m.id] = time()
                            with suppress(NotFound, Forbidden, HTTPException):
                                await msg.channel.delete_messages(messages)

                            # Don't mute users with Administrator
                            if user.top_role.position >= bot_user.top_role.position or user.guild_permissions.administrator:
                                continue
                            # Don't continue if lacking permission(s) to operate
                            if not msg.channel.permissions_for(bot_user).send_messages or not perms.manage_roles:
                                continue

                            try:
                                async with msg.channel.typing():
                                    mute_role = await self.bot.attrs.get_mute_role(msg.guild, upsert=True)
                                    if not mute_role or mute_role.position >= msg.guild.me.top_role.position:
                                        return
                            except NotFound:
                                return

                        if "antispam_mutes" not in self.bot.tasks:
                            self.bot.tasks["antispam_mutes"] = {}
                        if guild_id not in self.bot.tasks["antispam_mutes"]:
                            self.bot.tasks["antispam_mutes"][guild_id] = {}
                        if user_id in self.bot.tasks["antispam_mutes"][guild_id]:
                            task = self.bot.tasks["antispam_mutes"][guild_id][user_id]
                            if task.done():
                                if task.result():
                                    self.bot.log.critical(f"An antispam task errored.\n{task.result()}")
                                else:
                                    self.bot.log.critical(f"An antispam task errored with no result")
                            else:
                                return

                        self.bot.tasks["antispam_mutes"][guild_id][user_id] = self.bot.loop.create_task(
                            self.process_mute(
                                user_id=user.id,
                                guild_id=guild_id,
                                msg=msg,
                                reason=reason
                            )
                        )

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.mentions and not after.mentions:
            await self.on_message_delete(before)

    @commands.Cog.listener()
    async def on_message_delete(self, msg):
        """ Check deleted messages for ghost ping annoyances """
        if not msg.author.bot and msg.guild and (msg.raw_mentions or msg.reference):
            await self.config.cache(msg.guild.id)
            if self.config.get(msg.guild.id, {}).get("mass_pings", {}).get("ghost_pings", None):
                if not msg.guild.me.guild_permissions.view_audit_log:
                    return
                if msg.mentions and all(m.bot for m in msg.mentions) and not msg.reference:
                    return
                prefixes = await get_prefixes_async(self.bot, msg)
                if any(msg.content.startswith(p) for p in prefixes):
                    return
                if reference := getattr(msg.reference, "cached_message", None):
                    if reference.author.bot and not msg.raw_mentions:
                        return
                    target = reference.author
                else:
                    target = msg.mentions[0]

                # Only lose our shit over pings deleted within the last 2 minutes
                lmt = datetime.now(tz=timezone.utc) - timedelta(seconds=5)
                if msg.created_at > lmt:

                    # Check if any bots have deleted the message
                    async for entry in msg.guild.audit_logs(limit=1, action=discord.AuditLogAction.message_delete):
                        if entry.created_at > lmt:
                            return
                    async for entry in msg.guild.audit_logs(limit=1, action=discord.AuditLogAction.message_bulk_delete):
                        if entry.created_at > lmt:
                            return

                    # Check if chatfilter deleted the message
                    await asyncio.sleep(0.5)
                    if msg.guild.id in self.bot.filtered_messages:
                        if msg.id in self.bot.filtered_messages[msg.guild.id]:
                            return

                    # Mute if it's an obvious ghost ping
                    # if msg.created_at > datetime.now(tz=timezone.utc) - timedelta(seconds=5):
                    #     if msg.guild.id not in self.bot.tasks["antispam_mutes"]:
                    #         self.bot.tasks["antispam_mutes"][msg.guild.id] = {}
                    #     self.bot.tasks["antispam_mutes"][msg.guild.id][msg.author.id] = self.bot.loop.create_task(
                    #         self.process_mute(
                    #             user_id=msg.author.id,
                    #             guild_id=msg.guild.id,
                    #             msg=msg,
                    #             reason=f"Ghost ping\n"
                    #                    f"**Target:** {target}"
                    #         )
                    #     )
                    #     return

                    # Send a warning if not sure
                    e = discord.Embed(color=self.bot.config["theme_color"])
                    e.description = f"{msg.author.mention} no ghost pinging\n" \
                                    f"**Target:** {target}"
                    await msg.channel.send(
                        embed=e,
                        allowed_mentions=default_mentions
                    )

    @commands.Cog.listener()
    async def on_thread_join(self, thread: discord.Thread):
        """ Ensure users don't spam create threads """
        guild_id = thread.guild.id
        await self.config.cache(guild_id)
        if thread.guild.id in self.config and "duplicates" in self.config[guild_id]:
            if limit := self.config[guild_id]["duplicates"]["max_open_threads"]:
                if not thread.owner.guild_permissions.manage_threads:
                    total_open_threads = [
                        c for c in thread.parent.threads
                        if c.owner_id == thread.owner_id
                           and not c.archived
                    ]
                    if len(total_open_threads) > limit:
                        await thread.delete()
                        s = "s" if limit > 1 else ""
                        e = discord.Embed(color=self.bot.config["theme_color"])
                        e.description = f"{thread.owner.mention} you can only have {limit} open thread{s}"
                        await thread.parent.send(
                            embed=e,
                            delete_after=5,
                            allowed_mentions=default_mentions
                        )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """ Prevent users from spamming reactions on a single message """
        if payload.guild_id != 850956124168519700:
            return
        channel = self.bot.get_channel(payload.channel_id)
        msg = await channel.fetch_message(payload.message_id)  # type: ignore
        if len(msg.reactions) < 8:
            return
        single = []
        for r in msg.reactions:
            if r.count == 1:
                single.append(r)
        if len(single) > 2:
            for r in single:
                await msg.clear_reaction(r.emoji)

    @commands.Cog.listener()
    async def on_ready(self):
        """ Resume mute tasks when the bot is ready """
        if "antispam_mutes" not in self.bot.tasks:
            self.bot.tasks["antispam_mutes"] = {}
        mutes = await self.get_mutes()
        for guild_id, mutes in list(mutes.items()):
            for user_id, data in mutes.items():
                if guild_id not in self.bot.tasks["antispam_mutes"]:
                    self.bot.tasks["antispam_mutes"][guild_id] = {}
                if user_id not in self.bot.tasks["antispam_mutes"][guild_id]:
                    guild = self.bot.get_guild(int(guild_id))
                    if not guild:
                        await self.destroy_task(guild_id, user_id)
                        continue
                    try:
                        self.bot.tasks["antispam_mutes"][guild_id][user_id] = self.bot.loop.create_task(
                            self.process_mute(
                                guild_id=guild_id,
                                user_id=user_id,
                                msg=None,
                                reason="",
                                timer=round(float(data["end_time"]) - time()),
                                resume=True
                            )
                        )
                        self.bot.log.info(f"Resumed a anti_spam mute in {guild}")
                    except AttributeError:
                        await self.destroy_task(guild_id, user_id)
                        self.bot.log.info(f"Deleted a anti_spam task in {guild} due to changes")

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """ Remove timers if a users manually unmuted by a Moderator"""
        guild_id = before.guild.id
        user_id = before.id
        if "antispam_mutes" not in self.bot.tasks:
            self.bot.tasks["antispam_mutes"] = {}
        if guild_id in self.bot.tasks["antispam_mutes"]:
            if user_id in self.bot.tasks["antispam_mutes"][guild_id]:
                await asyncio.sleep(5)
                mute_role = await self.bot.attrs.get_mute_role(before.guild, upsert=False)
                if not mute_role:
                    return
                if mute_role not in after.roles:
                    await self.destroy_task(guild_id, user_id)
            # Clean up the index
            if guild_id in self.bot.tasks["antispam_mutes"]:
                if not self.bot.tasks["antispam_mutes"][guild_id]:
                    del self.bot.tasks["antispam_mutes"][guild_id]

    async def process_mute(self, guild_id, user_id, msg, reason="", resume=False, timer=0) -> Any:
        """
        Handle the entire muting process separately
        :param int guild_id:
        :param int user_id:
        :param Message or None msg:
        :param str reason:
        :param bool resume:
        :param int timer:
        """
        guild = self.bot.get_guild(int(guild_id))
        if not guild:
            return await self.destroy_task(guild_id, user_id)
        user = guild.get_member(int(user_id))
        if not user:
            return await self.destroy_task(guild_id, user_id)

        mute_role = await self.bot.attrs.get_mute_role(guild, upsert=True)
        if not mute_role or mute_role.position >= guild.me.top_role.position:
            return await self.destroy_task(guild_id, user_id)

        with self.bot.utils.operation_lock(key=int(user_id)):
            if not resume:
                bot_user = msg.guild.me
                perms = msg.channel.permissions_for(bot_user)
                if not perms.manage_messages or not perms.manage_roles:
                    return await self.destroy_task(guild_id, user_id)

                # Don't mute users with Administrator
                if user.top_role.position >= bot_user.top_role.position or user.guild_permissions.administrator:
                    return await self.destroy_task(guild_id, user_id)

                # Don't continue if lacking permission(s) to operate
                if not msg.channel.permissions_for(bot_user).send_messages or not perms.manage_roles:
                    return await self.destroy_task(guild_id, user_id)

                if not msg.channel:
                    return await self.destroy_task(guild_id, user_id)
                async with msg.channel.typing():
                    # Increase the mute timer if multiple offenses in the last hour
                    multiplier = 1
                    if guild_id not in self.mutes:
                        self.mutes[guild_id] = {}
                    if user_id not in self.mutes[guild_id]:
                        self.mutes[guild_id][user_id] = []
                    self.mutes[guild_id][user_id].append(time())
                    for mute_time in self.mutes[guild_id][user_id]:
                        if mute_time > time() - 3600:
                            multiplier += 1
                        else:
                            self.mutes[guild_id][user_id].remove(mute_time)

                    # Mute and purge any new messages
                    if mute_role in user.roles:
                        return await self.destroy_task(guild_id, user_id)

                    timer = 150
                    timer *= multiplier
                    end_time = time() + timer
                    timer_str = get_time(timer)

                    try:
                        await user.add_roles(mute_role)
                    except (NotFound, HTTPException) as e:
                        with suppress(Exception):
                            await msg.channel.send(f"Failed to mute {msg.author}. {e}")
                        return await self.destroy_task(guild_id, user_id)
                    except Forbidden:
                        with suppress(Exception):
                            await msg.channel.send(f"Failed to mute {msg.author}. Missing permissions")
                        return await self.destroy_task(guild_id, user_id)

                    messages = []
                    if user_id in self.msgs:
                        messages = [m for m in self.msgs[user_id] if m]
                    with suppress(Forbidden, NotFound, HTTPException):
                        await msg.channel.delete_messages(messages)
                    self.msgs[user_id] = []

                    with suppress(NotFound, Forbidden, HTTPException):
                        await user.send(f"You've been muted for spam in **{msg.guild.name}** for {timer_str}")
                    mentions = discord.AllowedMentions(users=True)
                    with suppress(NotFound, Forbidden, HTTPException):
                        await msg.channel.send(
                            f"Temporarily muted {user.mention} for spam. Reason: {reason}",
                            allowed_mentions=default_mentions
                        )

                    if "duplicate" in reason:
                        if msg.channel.permissions_for(msg.guild.me).manage_messages:
                            if msg.channel.permissions_for(msg.guild.me).read_message_history:
                                self.bot.loop.create_task(self.cleanup_from_message(msg))

                    with suppress(Exception):
                        async with self.bot.utils.cursor() as cur:
                            await cur.execute(
                                f"insert into anti_spam_mutes "
                                f"values ("
                                f"{msg.guild.id}, "
                                f"{msg.channel.id}, "
                                f"{msg.author.id}, "
                                f"{mute_role.id}, "
                                f"'{end_time}')"
                                f"on duplicate key update "
                                f"end_time = '{end_time}';"
                            )

            if timer > 3600:
                self.bot.log.critical(f"An antispam task is sleeping for {timer} seconds")

            await asyncio.sleep(timer)
            if user and mute_role and mute_role in user.roles:
                if not msg:
                    with suppress(NotFound, Forbidden, HTTPException):
                        await user.remove_roles(mute_role)
                else:
                    try:
                        await user.remove_roles(mute_role)
                    except Forbidden:
                        await msg.channel.send(f"Missing permissions to unmute {user.mention}")
                    except NotFound:
                        await msg.channel.send(f"Couldn't find and unmute **{user}**")
                    except HTTPException:
                        await msg.channel.send(f"Unknown error while unmuting {user.mention}")
                    else:
                        with suppress(Exception):
                            await msg.channel.send(
                                f"Unmuted **{user.mention}**",
                                allowed_mentions=discord.AllowedMentions(users=True)
                            )

            return await self.destroy_task(guild_id, user_id)


class ConfigureMenu(AuthorView):
    """ Select menu for the antispam configure command """
    class ConfigureSelect(ui.Select):
        def __init__(self, ctx: Context, module: str, main_view: "ConfigureMenu") -> None:
            self.ctx = ctx
            self.module = module
            self.main_view = main_view
            self.cog: AntiSpam = ctx.bot.cogs["AntiSpam"]
            conf = self.cog.config[ctx.guild.id][module]

            options = []
            if isinstance(conf, list) or "thresholds" in conf:
                options.append(SelectOption(
                    label="Add a threshold",
                    emoji="📌",
                    value="add_threshold"
                ))
                options.append(SelectOption(
                    label="View/Manage thresholds",
                    emoji="🔍",
                    value="remove_threshold"
                ))
            if not isinstance(conf, list):
                for key, value in conf.items():
                    if key == "thresholds":
                        continue
                    if key == "per_message":
                        options.append(SelectOption(
                            label=f"Set the per-message threshold ({value})",
                            emoji="🔗",
                            value=key
                        ))
                    elif isinstance(value, bool):
                        toggle = "Disable" if value else "Enable"
                        options.append(SelectOption(
                            label=f"{toggle} flagging {key.replace('_', ' ')}",
                            emoji="🛑" if value else "🚦",
                            value=key
                        ))
                    elif isinstance(value, int) or value is None:
                        label = f"Set the {key.replace('_', ' ')} cooldown"
                        if "max" in key:  # Account for the max threads option
                            label = label.rstrip(" cooldown")
                        if value is None:
                            label += " (Disabled)"
                        elif "threads" in key:
                            label += f" ({value})"
                        else:
                            label += f" ({value}s)"
                        options.append(SelectOption(
                            label=label,
                            emoji="⏳",
                            value=key
                        ))
            options.append(discord.SelectOption(
                label=f"Cancel Editing {module.title().replace('_', ' ')}",
                emoji="🚫",
                value="cancel"
            ))
            super().__init__(
                placeholder="Select which setting",
                min_values=1,
                max_values=1,
                options=options
            )

        async def callback(self, interaction: Interaction) -> None:
            guild_id = self.ctx.guild.id
            conf = self.cog.config[guild_id][self.module]
            key = interaction.data["values"][0]
            if key != "cancel":
                if key == "add_threshold":
                    await interaction.response.edit_message(
                        content="Choose the threshold. After that we'll set the timeframe for that threshold"
                    )
                    choices = [f"Limit to {num} msgs within X seconds" for num in thresholds]
                    choice = await GetChoice(self.ctx, choices, message=interaction.message, delete_after=False)
                    threshold = thresholds[choices.index(choice)]

                    await interaction.message.edit(
                        content="Choose a timeframe for that threshold"
                    )
                    choices = [f"Only allow X msgs within {num} seconds" for num in timespans]
                    choice = await GetChoice(self.ctx, choices, message=interaction.message, delete_after=False)
                    timeframe = timespans[choices.index(choice)]

                    new = {
                        "timespan": timeframe,
                        "threshold": threshold
                    }
                    items = self.cog.config[guild_id][self.module]
                    if isinstance(items, dict):
                        items = items["thresholds"]
                    if new in items:
                        await interaction.followup.send("That threshold already exits", ephemeral=True)
                    else:
                        if isinstance(conf, list):
                            self.cog.config[guild_id][self.module].append(new)
                        else:
                            self.cog.config[guild_id][self.module]["thresholds"].append(new)

                elif key == "remove_threshold":
                    if not conf and not (conf["thresholds"] if isinstance(conf, dict) else False):
                        await interaction.response.send_message("That module has no thresholds", ephemeral=True)
                    else:
                        await interaction.response.edit_message(content="Selecting a threshold removes it")
                        _thresholds = conf if isinstance(conf, list) else conf["thresholds"]
                        choices = ["Return to modules", *[
                            f"{c['threshold']} within {c['timespan']} seconds" for c in _thresholds if c
                        ]]
                        choice = await GetChoice(self.ctx, choices, message=interaction.message, delete_after=False)
                        if choices.index(choice) != 0:
                            threshold = _thresholds[choices.index(choice) - 1]
                            if isinstance(conf, list):
                                self.cog.config[guild_id][self.module].remove(threshold)
                            else:
                                self.cog.config[guild_id][self.module]["thresholds"].remove(threshold)

                elif isinstance(conf[key], bool):
                    # Toggle the value between True/False
                    self.cog.config[guild_id][self.module][key] = not conf[key]

                elif isinstance(conf[key], int) or conf[key] is None:
                    await interaction.response.edit_message(
                        content="Choose the threshold"
                    )
                    nums = list(per_each_timespans)
                    if "max" in key:  # Process the thread limit option differently
                        nums = [nums[0], 1, *nums[1:]]
                        choices = [
                            f"Set the limit to {num} open thread{'s' if num != 1 else ''} per user"
                            if isinstance(num, int) else num
                            for num in nums
                        ]
                    elif key == "per_message":
                        choices = [
                            f"Limit to {num} per message"
                            if isinstance(num, int) else num
                            for num in nums
                        ]
                    else:
                        choices = [
                            f"Limit to once every {num} seconds"
                            if isinstance(num, int) else num
                            for num in nums
                        ]
                    choice = await GetChoice(self.ctx, choices, message=interaction.message, delete_after=False)
                    if "None" in choice:
                        self.cog.config[guild_id][self.module][key] = None
                    else:
                        threshold = nums[choices.index(choice)]
                        self.cog.config[guild_id][self.module][key] = threshold

                await self.cog.config.flush()

            if not interaction.response.is_done():
                await interaction.response.defer()
            if interaction.message.content != "Select your choice":
                await interaction.message.edit(content="Select your choice")

            choices = list(self.cog.config[guild_id].keys())
            if "ignored" in choices:
                choices.remove("ignored")
            module = await GetChoice(self.ctx, choices, message=interaction.message, delete_after=False)
            self.main_view.__init__(self.ctx, module)
            await interaction.message.edit(view=self.main_view)

    def __init__(self, ctx: Context, module: str) -> None:
        self.ctx = ctx
        self.cd = ctx.bot.utils.cooldown_manager(2, 5)
        super().__init__(timeout=45)
        self.add_item(self.ConfigureSelect(ctx, module, self))

    async def on_error(self, error: Exception, item, interaction: Interaction) -> None:
        if not isinstance(error, (NotFound, IgnoredExit)):
            raise


def setup(bot):
    bot.add_cog(AntiSpam(bot), override=True)
