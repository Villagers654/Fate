"""
Core bot functions like:
Prefix, Invite, and Ping
"""

from bs4 import BeautifulSoup as bs
import json
from io import BytesIO
import requests
import aiohttp
from time import time, monotonic
from typing import Union
import asyncio

from discord.ext import commands
import discord
from discord import Webhook, AsyncWebhookAdapter
import dbl

from utils import config, colors, auth
from cogs.core.utils import Utils as utils


class Core(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last = {}
        self.spam_cd = {}
        creds = auth.TopGG()
        self.dblpy = dbl.DBLClient(
            self.bot, creds.token, autopost=True,
            webhook_path=creds.path, webhook_auth=creds.auth, webhook_port=creds.port
        )
        self.path = "./data/userdata/disabled_commands.json"

    async def on_guild_post(self):
        print("Server count posted successfully")

    @commands.Cog.listener()
    async def on_dbl_test(self, data):
        self.bot.log.info(f"Received a test upvote from {self.bot.get_user(int(data['user']))}")
        async with self.bot.cursor() as cur:
            await cur.execute(
                f"insert into votes values ({int(data['user'])}, {time()});"
            )

    @commands.Cog.listener()
    async def on_dbl_vote(self, data):
        self.bot.log.info(f"Received an upvote from {self.bot.get_user(int(data['user']))}")
        async with self.bot.cursor() as cur:
            await cur.execute(
                f"insert into votes values ({int(data['user'])}, {time()});"
            )

    @commands.command(name='dbl')
    @commands.is_owner()
    async def dbl(self, ctx):
        await ctx.send()

    @commands.command(name="votes")
    @commands.is_owner()
    async def votes(self, ctx):
        votes = await self.dblpy.get_bot_upvotes()
        await ctx.send(", ".join(dat["username"] for dat in votes))

    @commands.command(name="topguilds")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    async def topguilds(self, ctx):
        e = discord.Embed(color=0x80B0FF)
        e.title = "Top Guilds"
        e.description = ""
        rank = 1
        for guild in sorted(
            [[g.name, g.member_count] for g in self.bot.guilds],
            key=lambda k: k[1],
            reverse=True,
        )[:8]:
            e.description += "**{}.** {}: `{}`\n".format(rank, guild[0], guild[1])
            rank += 1
        await ctx.send(embed=e)

    @commands.command(name="invite", aliases=["links", "support"])
    @commands.cooldown(1, 5, commands.BucketType.channel)
    async def invite(self, ctx):
        await ctx.send(embed=config.links())

    @commands.command(name="vote")
    @commands.cooldown(1, 5, commands.BucketType.channel)
    async def vote(self, ctx):
        await ctx.send("https://top.gg/bot/506735111543193601")

    @commands.command(name="say")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.bot_has_permissions(attach_files=True)
    async def say(self, ctx, *, content: commands.clean_content = None):
        has_perms = ctx.channel.permissions_for(ctx.guild.me).manage_messages
        if len(str(content).split("\n")) > 4:
            await ctx.send(f"{ctx.author.mention} too many lines")
            if has_perms and ctx.message:
                await ctx.message.delete()
            return
        if content:
            content = utils.cleanup_msg(ctx.message, content)
            content = content[:2000]
        if ctx.message.attachments and ctx.channel.is_nsfw():
            file_data = [
                (f.filename, BytesIO(requests.get(f.url).content))
                for f in ctx.message.attachments
            ]
            files = [
                discord.File(file, filename=filename) for filename, file in file_data
            ]
            await ctx.send(content, files=files)
            if has_perms:
                await ctx.message.delete()
        elif content and not ctx.message.attachments:
            await ctx.send(content)
            if has_perms and ctx.message:
                await ctx.message.delete()
        elif ctx.message.attachments:
            await ctx.send("You can only attach files if the channel's nsfw")
        else:
            await ctx.send("Content is a required argument that is missing")

    @commands.command(name="prefix")
    @commands.cooldown(*utils.default_cooldown())
    @commands.guild_only()
    async def _prefix(self, ctx, *, prefix=None):
        async with self.bot.open("./data/userdata/config.json", "r") as f:
            config = json.loads(await f.read())  # type: dict
        guild_id = str(ctx.guild.id)
        if not prefix:
            prefixes = ""
            if guild_id in config["prefix"]:
                prefixes += f"**Guild Prefix:** `{config['prefix'][guild_id]}`"
            else:
                prefixes += f"**Guild Prefix:** `.`"
            if str(ctx.author.id) in config["personal_prefix"]:
                prefixes += f"**Personal Prefix:** `{config['personal_prefix'][str(ctx.author.id)]}`"
            e = discord.Embed(color=colors.fate())
            e.set_author(name="Prefixes", icon_url=ctx.author.avatar_url)
            e.description = prefixes
            return await ctx.send(embed=e)
        if not ctx.author.guild_permissions.manage_guild:
            return await ctx.send(f"You need manage_server permission(s) to use this")
        if not isinstance(ctx.guild, discord.Guild):
            return await ctx.send("This command can't be used in dm")
        async with self.bot.open("./data/userdata/config.json", "w") as f:
            if "prefix" not in config:
                config["prefix"] = {}
            config["prefix"][guild_id] = prefix
            await f.write(json.dumps(config))
        await ctx.send(f"Changed the servers prefix to `{prefix}`")

    @commands.command(name="personal-prefix", aliases=["pp"])
    @commands.cooldown(*utils.default_cooldown())
    async def personal_prefix(self, ctx, *, prefix=""):
        user_id = str(ctx.author.id)
        async with self.bot.open("./data/userdata/config.json", "r") as f:
            config = json.loads(await f.read())  # type: dict
        if "personal_prefix" not in config:
            config["personal_prefix"] = {}
        config["personal_prefix"][user_id] = prefix
        if prefix == ".":
            del config["personal_prefix"][user_id]
        async with self.bot.open("./data/userdata/config.json", "w") as f:
            await f.write(json.dumps(config))
        await ctx.send(
            f"Set your personal prefix as `{prefix}`\n"
            f"Note you can still use my mention as a sub-prefix"
        )

    @commands.command(name="enable-command", aliases=["enablecommand"])
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(embed_links=True)
    async def enable_command(
        self,
        ctx,
        command,
        *,
        location: Union[discord.TextChannel, discord.CategoryChannel] = None,
    ):
        """Enable or commands in a channel, or category"""
        async with self.bot.open(self.path, "r") as f:
            config = json.loads(await f.read())  # type: dict
        guild_id = str(ctx.guild.id)
        if guild_id not in config:
            config[guild_id] = {
                "global": [],
                "channels": {},
                "categories": {},
            }
        conf = config[guild_id]
        if not location:
            options = [
                "Enable In All Channels",
                "Enable in This Category",
                "Enable in This Channel",
            ]
            choice = await self.bot.get_choice(
                ctx, *options, user=ctx.author, timeout=45
            )
            if not choice:
                return
            index = options.index(choice)
            enabled = False

            if index == 0:  # Globally
                if command in conf["global"]:
                    conf["global"].remove(command)
                    enabled = True
                for category_id, disabled_commands in conf["categories"].items():
                    if command in disabled_commands:
                        conf["categories"][category_id].remove(command)
                        enabled = True
                for channel_id, disabled_commands in conf["channels"].items():
                    if command in disabled_commands:
                        conf["channels"][channel_id].remove(command)
                        enabled = True
                if enabled:
                    await ctx.send(f"Globally enabled {command}")
                else:
                    await ctx.send(f"{command} isn't disabled anywhere")

            elif index == 1:  # Category
                if not ctx.channel.category:
                    return await ctx.send("This channel has no category")
                category_id = str(ctx.channel.category.id)
                for channel_id in [
                    str(channel.id) for channel in ctx.channel.category.channels
                ]:
                    if channel_id in conf["channels"]:
                        if command in conf["channels"][channel_id]:
                            conf["channels"][channel_id].remove(command)
                            enabled = True
                if category_id not in conf["categories"]:
                    conf["categories"][category_id] = []
                if command in conf["categories"][category_id]:
                    conf["categories"][category_id].remove(command)
                    enabled = True
                if enabled:
                    await ctx.send(f"Enabled {command} in {ctx.channel.category}")
                else:
                    await ctx.send(f"{command} isn't disabled in this category")

            elif index == 2:  # Channel
                channel_id = str(ctx.channel.id)
                if channel_id not in conf["channels"]:
                    conf["channels"][channel_id] = []
                if command not in conf["channels"][channel_id]:
                    return await ctx.send(f"{command} isn't disabled in this channel")
                conf["channels"][channel_id].remove(command)
                await ctx.send(f"Disabled {command} in {ctx.channel.mention}")

        elif isinstance(location, discord.TextChannel):
            channel_id = str(location.id)
            if channel_id not in conf["channels"]:
                return await ctx.send("That channel has no disabled commands")
            if command not in conf["channels"][channel_id]:
                return await ctx.send(f"{command} isn't disabled in that channel")
            conf["channels"][channel_id].remove(command)
            await ctx.send(f"Enabled {command} in that channel")
        elif isinstance(location, discord.CategoryChannel):
            channel_id = str(location.id)
            if channel_id not in conf["categories"]:
                return await ctx.send("That category has no disabled commands")
            if command not in conf["categories"][channel_id]:
                return await ctx.send(f"{command} isn't disabled in that category")
            conf["categories"][channel_id].remove(command)
            await ctx.send(f"Enabled {command} in that category")
        for channel_id, values in list(conf["channels"].items()):
            if not values:
                del conf["channels"][channel_id]
        for channel_id, values in list(conf["categories"].items()):
            if not values:
                del conf["categories"][channel_id]
        config[guild_id] = conf
        async with self.bot.open(self.path, "w") as f:
            await f.write(json.dumps(config))

    @commands.command(name="disable-command", aliases=["disablecommand"])
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(embed_links=True)
    async def disable_command(
        self,
        ctx,
        command,
        *,
        location: Union[discord.TextChannel, discord.CategoryChannel] = None,
    ):
        """Enable or commands in a channel, or category"""
        command = command.lower()
        if command == "disable" or command == "enable" or "lucky" in command:
            return await ctx.send("BiTcH nO")
        if command not in [cmd.name for cmd in self.bot.commands]:
            return await ctx.send("That's not a command")
        async with self.bot.open(self.path, "r") as f:
            config = json.loads(await f.read())  # type: dict
        guild_id = str(ctx.guild.id)
        if guild_id not in config:
            config[guild_id] = {
                "global": [],
                "channels": {},
                "categories": {},
            }
        conf = config[guild_id]

        if not location:
            options = [
                "Disable In All Channels",
                "Disable in This Category",
                "Disable in This Channel",
            ]
            choice = await self.bot.get_choice(
                ctx, *options, user=ctx.author, timeout=45
            )
            if not choice:
                return
            index = options.index(choice)

            if index == 0:  # Globally
                if command in conf["global"]:
                    return await ctx.send(f"{command} is already disabled")
                conf["global"].append(command)
                await ctx.send(f"Globally disabled {command}")

            elif index == 1:  # Category
                if not ctx.channel.category:
                    return await ctx.send("This channel has no category")
                category_id = str(ctx.channel.category.id)
                if category_id not in conf["categories"]:
                    conf["categories"][category_id] = []
                if command in conf["categories"][category_id]:
                    return await ctx.send(
                        f"{command} is already disabled in this category"
                    )
                conf["categories"][category_id].append(command)
                await ctx.send(f"Disabled {command} in {ctx.channel.category}")

            elif index == 2:  # Channel
                channel_id = str(ctx.channel.id)
                if channel_id not in conf["channels"]:
                    conf["channels"][channel_id] = []
                if command in conf["channels"][channel_id]:
                    return await ctx.send(
                        f"{command} is already disabled in this channel"
                    )
                conf["channels"][channel_id].append(command)
                await ctx.send(f"Disabled {command} in {ctx.channel.mention}")

        elif isinstance(location, discord.TextChannel):
            if str(location.id) not in conf["channels"]:
                conf["channels"][str(location.id)] = []
            if command in conf["channels"][str(location.id)]:
                return await ctx.send(f"{command} is already disabled in that channel")
            conf["channels"][str(location.id)].append(command)
            await ctx.send(f"Disabled {command} in that channel")
        elif isinstance(location, discord.CategoryChannel):
            if str(location.id) not in conf["categories"]:
                conf["categories"][str(location.id)] = []
            if command in conf["categories"][str(location.id)]:
                return await ctx.send(f"{command} is already disabled in that category")
            conf["categories"][str(location.id)].append(command)
            await ctx.send(f"Disabled {command} in that category")
        config[guild_id] = conf
        async with self.bot.open(self.path, "w") as f:
            await f.write(json.dumps(config))

    @commands.command(name="disabled")
    @commands.cooldown(1, 5, commands.BucketType.channel)
    @commands.has_permissions(administrator=True)
    async def disabled(self, ctx):
        """ Lists the guilds disabled commands """
        async with self.bot.open(self.path, "r") as f:
            config = json.loads(await f.read())  # type: dict
        guild_id = str(ctx.guild.id)
        conf = config[guild_id]
        if guild_id not in config or not any(
            conf[key]
            if isinstance(conf[key], list)
            else any(v[1] for v in conf[key].items())
            for key in conf.keys()
        ):
            return await ctx.send("There are no disabled commands")
        e = discord.Embed(color=colors.fate())
        if config[guild_id]["global"]:
            e.add_field(name="Global", value=", ".join(conf["global"]), inline=False)
        channels = {}
        dat = [*conf["channels"].items(), *conf["categories"].items()]
        for channel_id, commands in dat:
            await asyncio.sleep(0)
            if commands:
                channel = self.bot.get_channel(int(channel_id))
                if channel:
                    channels[channel] = []
                    for cmd in commands:
                        await asyncio.sleep(0)
                        channels[channel].append(cmd)
        for channel, commands in channels.items():
            await asyncio.sleep(0)
            e.add_field(name=channel.name, value=", ".join(commands), inline=False)
        await ctx.send(embed=e)

    @commands.command(name="ping")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    async def ping(self, ctx):
        e = discord.Embed(color=colors.fate())
        e.set_author(name="Measuring ping:")
        before = monotonic()
        message = await ctx.send(embed=e)
        ping = (monotonic() - before) * 1000
        if ping < 175:
            img = "https://cdn.discordapp.com/emojis/562592256939393035.png?v=1"
        else:
            if ping < 250:
                img = "https://cdn.discordapp.com/emojis/562592178204049408.png?v=1"
            else:
                if ping < 400:
                    img = "https://cdn.discordapp.com/emojis/562592177692213248.png?v=1"
                else:
                    if ping < 550:
                        img = "https://cdn.discordapp.com/emojis/562592176463151105.png?v=1"
                    else:
                        if ping < 700:
                            img = "https://cdn.discordapp.com/emojis/562592175880405003.png?v=1"
                        else:
                            img = "https://cdn.discordapp.com/emojis/562592175192539146.png?v=1"
        api = str(self.bot.latency * 1000)
        api = api[: api.find(".")]
        e.set_author(name=f"Bots Latency", icon_url=self.bot.user.avatar_url)
        e.set_thumbnail(url=img)
        e.description = (
            f"**Message Trip:** `{int(ping)}ms`\n**Websocket Heartbeat:** `{api}ms`"
        )
        await message.edit(embed=e)

    @commands.command(name="devping")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    async def devping(self, ctx):
        e = discord.Embed(color=colors.fate())
        e.set_author(name="Measuring ping:")
        before = monotonic()
        message = await ctx.send(embed=e)
        ping = (monotonic() - before) * 1000

        if ping < 175:
            img = "https://cdn.discordapp.com/emojis/562592256939393035.png?v=1"
        elif ping < 250:
            img = "https://cdn.discordapp.com/emojis/562592178204049408.png?v=1"
        elif ping < 400:
            img = "https://cdn.discordapp.com/emojis/562592177692213248.png?v=1"
        elif ping < 550:
            img = "https://cdn.discordapp.com/emojis/562592176463151105.png?v=1"
        elif ping < 700:
            img = "https://cdn.discordapp.com/emojis/562592175880405003.png?v=1"
        else:
            img = "https://cdn.discordapp.com/emojis/562592175192539146.png?v=1"

        api = str(self.bot.latency * 1000)
        api = api[: api.find(".")]
        e.set_author(name=f"Bots Latency", icon_url=self.bot.user.avatar_url)
        e.set_thumbnail(url=img)
        e.description = (
            f"**Message Trip 1:** `{int(ping)}ms`\n**Websocket Heartbeat:** `{api}ms`"
        )

        before = monotonic()
        await message.edit(embed=e)
        edit_ping = (monotonic() - before) * 1000
        e.description = f"**Message Trip 1:** `{int(ping)}ms`\n**Msg Edit Trip:** `{int(edit_ping)}ms`\n**Websocket Heartbeat:** `{api}ms`"

        before = monotonic()
        await message.edit(embed=e)
        second_edit_ping = (monotonic() - before) * 1000

        before = monotonic()
        await ctx.send("Measuring Ping", delete_after=0.5)
        second_ping = (monotonic() - before) * 1000
        e.description = f"**Message Trip 1:** `{int(ping)}ms`\n**Message Trip 2:** `{int(second_ping)}ms`\n**Msg Edit Trip 1:** `{int(edit_ping)}ms`\n**Msg Edit Trip 2:** `{int(second_edit_ping)}ms`\n**Websocket Heartbeat:** `{api}ms`"
        await message.edit(embed=e)

    @commands.is_nsfw()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    async def ud(self, ctx, *, query: str):
        channel_id = str(ctx.channel.id)
        if channel_id not in self.last:
            self.last[channel_id] = (None, None)
        if query == self.last[channel_id][0]:
            if self.last[channel_id][1] > time() - 60:
                return await ctx.message.add_reaction("❌")
        self.last[channel_id] = (query, time())
        url = "http://www.urbandictionary.com/define.php?term={}".format(
            query.replace(" ", "%20")
        )
        async with aiohttp.ClientSession() as sess:
            async with sess.get(url) as resp:
                r = await resp.read()
        resp = bs(r, "html.parser")
        try:
            if (
                len(
                    resp.find("div", {"class": "meaning"})
                    .text.strip("\n")
                    .replace("\u0027", "'")
                )
                >= 1000
            ):
                meaning = (
                    resp.find("div", {"class": "meaning"})
                    .text.strip("\n")
                    .replace("\u0027", "'")[:1000]
                    + "..."
                )
            else:
                meaning = (
                    resp.find("div", {"class": "meaning"})
                    .text.strip("\n")
                    .replace("\u0027", "'")
                )
            e = discord.Embed(color=0x80B0FF)
            e.set_author(name=f"{query} 🔍", icon_url=ctx.author.avatar_url)
            e.set_thumbnail(
                url="https://cdn.discordapp.com/attachments/450528552199258123/524139193723781120/urban-dictionary-logo.png"
            )
            e.description = "**Meaning:**\n{}\n\n**Example:**\n{}\n".format(
                meaning, resp.find("div", {"class": "example"}).text.strip("\n")
            )

            e.set_footer(
                text="~{}".format(
                    resp.find("div", {"class": "contributor"}).text.strip("\n")
                )
            )
            await ctx.send(embed=e)
        except AttributeError:
            await ctx.send(
                "Either the page doesn't exist, or you typed it in wrong. Either way, please try again."
            )
        except Exception as e:
            await ctx.send(f"**```ERROR: {type(e).__name__} - {e}```**")

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if isinstance(msg.channel, discord.DMChannel):
            user_id = msg.author.id
            now = int(time() / 5)
            if user_id not in self.spam_cd:
                self.spam_cd[user_id] = [now, 0]
            if self.spam_cd[user_id][0] == now:
                self.spam_cd[user_id][1] += 1
            else:
                self.spam_cd[user_id] = [now, 0]
            if self.spam_cd[user_id][1] < 2 or msg.author.bot:
                async with aiohttp.ClientSession() as session:
                    webhook = Webhook.from_url(
                        "https://discordapp.com/api/webhooks/673290242819883060/GDXiMBwbzw7dbom57ZupHsiEQ76w8TfV_mEwi7_pGw8CvVFL0LNgwRwk55yRPxNdPA4b",
                        adapter=AsyncWebhookAdapter(session),
                    )
                    msg.content = discord.utils.escape_mentions(msg.content)
                    if msg.attachments:
                        for attachment in msg.attachments:
                            return await webhook.send(
                                username=msg.author.name,
                                avatar_url=msg.author.avatar_url,
                                content=msg.content,
                                file=discord.File(
                                    BytesIO(requests.get(attachment.url).content),
                                    filename=attachment.filename,
                                ),
                            )
                    if msg.embeds:
                        if msg.author.id == self.bot.user.id:
                            return await webhook.send(
                                username=f"{msg.author.name} --> {msg.channel.recipient.name}",
                                avatar_url=msg.author.avatar_url,
                                embed=msg.embeds[0],
                            )
                        return await webhook.send(
                            username=msg.author.name,
                            avatar_url=msg.author.avatar_url,
                            embed=msg.embeds[0],
                        )
                    if msg.author.id == self.bot.user.id:
                        e = discord.Embed(color=colors.fate())
                        e.set_author(
                            name=msg.channel.recipient,
                            icon_url=msg.channel.recipient.avatar_url,
                        )
                        return await webhook.send(
                            username=msg.author.name,
                            avatar_url=msg.author.avatar_url,
                            content=msg.content,
                            embed=e,
                        )
                    await webhook.send(
                        username=msg.author.name,
                        avatar_url=msg.author.avatar_url,
                        content=msg.content,
                    )


def setup(bot):
    bot.add_cog(Core(bot))