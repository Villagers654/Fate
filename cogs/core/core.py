"""
cogs.core.core.py
~~~~~~~~~~~~~~~~~~

Core bot commands such as prefix, invite, and ping

:copyright: (C) 2019-present Michael Stollings
:license: Proprietary and Confidential, see LICENSE for details
"""

import aiohttp
from time import time, monotonic
import asyncio
from datetime import datetime, timezone, timezone
from contextlib import suppress

from discord.ext import commands
import discord
from discord import Webhook
import dbl

from botutils import colors, get_prefixes_async, cleanup_msg, emojis, Conversation


class Core(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last = {}
        self.spam_cd = {}
        creds = bot.auth["TopGG"]  # type: dict
        self.dblpy = dbl.DBLClient(
            bot=self.bot,
            token=creds["token"],
            autopost=True,
            webhook_path=creds["path"],
            webhook_auth=creds["auth"],
            webhook_port=creds["port"]
        )
        self.path = "./data/userdata/disabled_commands.json"
        self.config = bot.utils.cache("disabled")

        self.setup_usage = "Helps you set the bot up via conversation"

    async def on_guild_post(self):
        self.bot.log.debug("Server count posted successfully")

    @commands.Cog.listener()
    async def on_dbl_test(self, data):
        self.bot.log.info(f"Received a test upvote from {self.bot.get_user(int(data['user']))}")
        async with self.bot.utils.cursor() as cur:
            await cur.execute(
                f"insert into votes values ({int(data['user'])}, {time()});"
            )

    @commands.Cog.listener()
    async def on_dbl_vote(self, data):
        self.bot.log.info(f"Received an upvote from {self.bot.get_user(int(data['user']))}")
        async with self.bot.utils.cursor() as cur:
            await cur.execute(
                f"insert into votes values ({int(data['user'])}, {time()});"
            )

    @commands.command(name="votes")
    @commands.is_owner()
    async def votes(self, ctx):
        votes = await self.dblpy.get_bot_upvotes()
        await ctx.send(", ".join(dat["username"] for dat in votes))

    @commands.command(name="setup")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def setup(self, ctx):
        await ctx.send("Note this cmd doesn't actually do anything", delete_after=5)
        convo = Conversation(ctx)
        await convo.send(
            "To follow with setup just reply with `yes/no` for whether or not you want "
            "to use the given module. To stop just send `cancel`."
        )

        # Set the prefix
        reply = await convo.ask("To start, what's the command prefix you want me to have")
        await self.bot.get_command("prefix")(ctx, prefix=reply.content)

        # Anti Spam
        reply = await convo.ask("Do you want to use AntiSpam to mute any spammers I detect?", use_buttons=True)
        if reply:
            await convo.send("Alright, you can customize this more with `.antispam configure`")
            await self.bot.get_command("antispam enable")(ctx)

        # Logger
        reply = await convo.ask(
            "Do you want a logs channel set to show things like deleted messages? if so #mention the channel"
        )
        if reply.channel_mentions:
            channel = reply.channel_mentions[0]
            await self.bot.get_command("log setchannel")(ctx, channel=channel)

        # Verification
        reply = await convo.ask("Do you want users to verify via a captcha when they join the server?", use_buttons=True)
        if reply:
            await self.bot.get_command("verification enable")(ctx)

        await convo.send("Setup complete")

    @commands.command(name="topguilds")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    async def topguilds(self, ctx):
        e = discord.Embed(color=0x80B0FF)
        e.title = "Top Guilds"
        e.description = ""
        rank = 1
        items = [[g.name, g.member_count] for g in self.bot.guilds]
        for guild, count in sorted(items, key=lambda k: k[1], reverse=True, )[:8]:
            e.description += f"**{rank}.** {guild}: `{count}`\n"
            rank += 1
        await ctx.send(embed=e)

    @staticmethod
    def topguilds_usage():
        return "Displays the top 8 servers based on highest member count"

    @commands.command(name="invite", aliases=["links", "support"])
    @commands.cooldown(1, 5, commands.BucketType.channel)
    async def invite(self, ctx):
        embed = discord.Embed(color=0x80B0FF)
        embed.set_author(
            name=f"| Links | 📚",
            icon_url="https://images-ext-1.discordapp.net/external/kgeJxDOsmMoy2gdBr44IFpg5hpYzqxTkOUqwjYZbPtI/%3Fsize%3D1024/https/cdn.discordapp.com/avatars/506735111543193601/689cf49cf2435163ca420996bcb723a5.webp",
        )
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/501871950260469790/513636736492896271/mail-open-solid.png")
        embed.description = (
            f"[Invite]({self.bot.invite_url}) 📥\n"
            f"[Support](https://discord.gg/wtjuznh) 📧\n"
            f"[Discord](https://discord.gg/wtjuznh) <:discord:513634338487795732>\n"
            f"[Vote](https://top.gg/bot/506735111543193601) ⬆"
        )
        await ctx.send(embed=embed)

    @staticmethod
    def invite_usage():
        return "Gives the link to invite the bot to another server. " \
               "Alongside the invite to the support server. Just click the blue hyperlink text"

    @commands.command(name="vote", usage="Sends the link to vote for the bot on top.gg")
    @commands.cooldown(1, 5, commands.BucketType.channel)
    async def vote(self, ctx):
        await ctx.send("https://top.gg/bot/506735111543193601/vote")

    @commands.command(name="say")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    @commands.bot_has_permissions(attach_files=True)
    async def say(self, ctx, *, content: commands.clean_content):
        has_perms = ctx.channel.permissions_for(ctx.guild.me).manage_messages
        if len(str(content).split("\n")) > 4:
            await ctx.send(f"{ctx.author.mention} too many lines")
            if has_perms and ctx.message:
                await ctx.message.delete()
            return
        if len(str(content)) > 100:
            return await ctx.send("That's too long")
        content = cleanup_msg(ctx.message, content)
        await ctx.send(content, allowed_mentions=discord.AllowedMentions.none())
        if has_perms and ctx.message:
            await ctx.message.delete()

    @commands.command(name="prefix")
    @commands.cooldown(2, 5, commands.BucketType.user)
    @commands.guild_only()
    async def prefix(self, ctx, *, prefix = None):
        if not prefix:
            prefixes = await get_prefixes_async(self.bot, ctx.message)
            formatted = "\n".join(prefixes[1::])
            e = discord.Embed(color=colors.fate)
            e.set_author(name="Prefixes", icon_url=ctx.author.avatar.url)
            e.description = formatted
            return await ctx.send(embed=e)
        if not ctx.author.guild_permissions.manage_guild:
            return await ctx.send(f"You need manage_server permission(s) to use this")
        if not isinstance(ctx.guild, discord.Guild):
            return await ctx.send("This command can't be used in dm")
        if len(prefix) > 5:
            return await ctx.send("That prefix is too long")
        opts = ["yes", "no"]
        choice = await self.bot.utils.get_choice(ctx, opts, name="Allow personal prefixes?")
        override = True if choice == "no" else False
        if ctx.guild.id in self.bot.guild_prefixes:
            if not override and prefix == ".":
                await self.bot.aio_mongo["GuildPrefixes"].delete_one({
                    "_id": ctx.guild.id
                })
                del self.bot.guild_prefixes[ctx.guild.id]
                return await ctx.send("Reset the prefix to default")
            else:
                await self.bot.aio_mongo["GuildPrefixes"].update_one(
                    filter={"_id": ctx.guild.id},
                    update={"$set": {"prefix": prefix, "override": override}}
                )
        else:
            if not override and prefix == ".":
                return await ctx.send("tHaT's tHe sAmE aS thE cuRreNt cOnfiG")
            await self.bot.aio_mongo["GuildPrefixes"].insert_one({
                "_id": ctx.guild.id,
                "prefix": prefix,
                "override": override
            })
        self.bot.guild_prefixes[ctx.guild.id] = {
            "prefix": prefix,
            "override": override
        }
        await ctx.send(f"Changed the servers prefix to `{prefix}`")

    @commands.command(name="personal-prefix", aliases=["pp"])
    @commands.cooldown(2, 5, commands.BucketType.user)
    async def personal_prefix(self, ctx, *, prefix=""):
        if prefix.startswith('"') and prefix.endswith('"') and len(prefix) > 2:
            prefix = prefix.strip('"')
        prefix = prefix.strip("'\"")
        if len(prefix) > 8:
            return await ctx.send("Your prefix can't be more than 8 chars long")
        if ctx.author.id in self.bot.user_prefixes:
            await self.bot.aio_mongo["UserPrefixes"].update_one(
                filter={"_id": ctx.author.id},
                update={"$set": {"prefix": prefix}}
            )
        else:
            await self.bot.aio_mongo["UserPrefixes"].insert_one({
                "_id": ctx.author.id,
                "prefix": prefix
            })
        self.bot.user_prefixes[ctx.author.id] = {"prefix": prefix}
        nothing = "something that doesn't exist"
        await ctx.send(
            f"Set your personal prefix as `{prefix if prefix else nothing}`\n"
            f"Note you can still use my mention as a sub-prefix"
        )

    @commands.command(name="enable-command", aliases=["enablecommand"])
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(embed_links=True)
    async def enable_command(self, ctx, *, command):
        guild_id = ctx.guild.id
        if guild_id not in self.config:
            return await ctx.send("This server has no disabled commands")
        if not self.bot.get_command(command):
            return await ctx.send("That's not a command")
        command = self.bot.get_command(command).name
        for key, value in list(self.config[guild_id].items()):
            await asyncio.sleep(0)
            if command in value:
                break
        else:
            return await ctx.send(f"`{command}` isn't disabled anywhere")
        locations = [
            "enable globally", "enable in category", "enable in this channel"
        ]
        choice = await self.bot.utils.get_choice(ctx, locations, user=ctx.author)
        if not choice:
            return
        if choice == "enable globally":
            for key, value in list(self.config[guild_id].items()):
                await asyncio.sleep(0)
                if command in value:
                    self.config[guild_id][key].remove(command)
                    if not self.config[guild_id][key]:
                        await self.config.remove_sub(guild_id, key)
            await ctx.send(f"Enabled `{command}` in all channels")
        elif choice == "enable in category":
            if not ctx.channel.category:
                return await ctx.send("This channel has no category")
            for channel in ctx.channel.category.text_channels:
                await asyncio.sleep(0)
                channel_id = str(channel.id)
                if channel_id in self.config[guild_id]:
                    if command in self.config[guild_id][channel_id]:
                        self.config[guild_id][channel_id].remove(command)
                        if not self.config[guild_id][channel_id]:
                            await self.config.remove_sub(guild_id, channel_id)
            await ctx.send(f"Enabled `{command}` in all of {ctx.channel.category}'s channels")
        elif choice == "enable in this channel":
            channel_id = str(ctx.channel.id)
            if channel_id not in self.config[guild_id]:
                return await ctx.send("This channel has no disabled commands")
            if command not in self.config[guild_id][channel_id]:
                return await ctx.send(f"`{command}` isn't disabled in this channel")
            self.config[guild_id][channel_id].remove(command)
            if not self.config[guild_id][channel_id]:
                await self.config.remove_sub(guild_id, key)
            await ctx.send(f"Enabled `{command}` in this channel")
        if not self.config[guild_id]:
            await self.config.remove(guild_id)
        else:
            await self.config.flush()

    @commands.command(name="disable-command", aliases=["disablecommand"])
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(embed_links=True)
    async def disable_command(self, ctx, *, command):
        if "enable" in command.lower() or "disable" in command.lower():
            return await ctx.send("You can't disable commands with 'enable' or 'disable' in them")
        guild_id = ctx.guild.id
        if not self.bot.get_command(command):
            return await ctx.send("That's not a command")
        if guild_id not in self.config:
            self.config[guild_id] = {}
        command = self.bot.get_command(command).name
        locations = [
            "disable globally", "disable in category", "disable in this channel"
        ]
        choice = await self.bot.utils.get_choice(ctx, locations, user=ctx.author)
        if not choice:
            return
        if guild_id not in self.config:
            self.config[guild_id] = {}
        if choice == "disable globally":
            for channel in ctx.guild.text_channels:
                await asyncio.sleep(0)
                channel_id = str(channel.id)
                if channel_id not in self.config[guild_id]:
                    self.config[guild_id][channel_id] = []
                if command not in self.config[guild_id][channel_id]:
                    self.config[guild_id][channel_id].append(command)
            await ctx.send(f"Disabled `{command}` in all existing channels")
        elif choice == "disable in category":
            if not ctx.channel.category:
                return await ctx.send("This channel has no category")
            for channel in ctx.channel.category.text_channels:
                await asyncio.sleep(0)
                channel_id = str(channel.id)
                if channel_id not in self.config[guild_id]:
                    self.config[guild_id][channel_id] = []
                if command not in self.config[guild_id][channel_id]:
                    self.config[guild_id][channel_id].append(command)
            await ctx.send(f"Disabled `{command}` in all of {ctx.channel.category}'s channels")
        elif choice == "disable in this channel":
            channel_id = str(ctx.channel.id)
            if channel_id not in self.config[guild_id]:
                self.config[guild_id][channel_id] = []
            if command not in self.config[guild_id][channel_id]:
                self.config[guild_id][channel_id].append(command)
            self.config[guild_id][channel_id].remove(command)
            await ctx.send(f"Disabled `{command}` in this channel")
        await self.config.flush()

    @commands.command(name="disabled", aliases=["disabled-commands", "disabledcommands"])
    @commands.cooldown(1, 5, commands.BucketType.channel)
    @commands.has_permissions(administrator=True)
    async def disabled(self, ctx):
        """ Lists the guilds disabled commands """
        guild_id = ctx.guild.id
        if guild_id not in self.config:
            return await ctx.send("This server has no disabled commands")
        e = discord.Embed(color=discord.Color.red())
        for channel_id, commands in self.config[guild_id].items():
            await asyncio.sleep(0)
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                continue
            e.add_field(name=channel.name, value=", ".join([f"`{c}`" for c in commands]))
        await ctx.send(embed=e)

    @commands.command(name="ping")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    async def ping(self, ctx):
        e = discord.Embed(color=colors.fate)
        e.set_author(name="Measuring ping:")
        before = monotonic()
        msg = await ctx.send(embed=e)
        api_ping = f"{emojis.discord} **Discord API:** `{round((monotonic() - before) * 1000)}ms`"
        response_time = (datetime.now(tz=timezone.utc) - ctx.message.created_at).total_seconds() * 1000
        response_ping = f"\n{emojis.verified} **Message Trip:** `{round(response_time)}ms`"
        imgs = [
            "https://cdn.discordapp.com/emojis/562592256939393035.png?v=1",
            "https://cdn.discordapp.com/emojis/562592178204049408.png?v=1",
            "https://cdn.discordapp.com/emojis/562592177692213248.png?v=1",
            "https://cdn.discordapp.com/emojis/562592176463151105.png?v=1",
            "https://cdn.discordapp.com/emojis/562592175880405003.png?v=1",
            "https://cdn.discordapp.com/emojis/562592175192539146.png?v=1"
        ]
        for i, limit in enumerate(range(175, 175 * 6, 175)):
            if response_time < limit:
                img = imgs[i]
                break
        else:
            img = imgs[5]
        shard_ping = ""
        for shard, latency in self.bot.latencies:
            shard_ping += f"\n{emojis.boost} **Shard {shard}:** `{round(latency * 1000)}ms`"
        e.set_author(name=f"Bots Latency", icon_url=self.bot.user.avatar.url)
        e.set_thumbnail(url=img)
        e.description = api_ping + response_ping + shard_ping
        await msg.edit(embed=e)

    @commands.command(name="devping")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    async def devping(self, ctx):
        e = discord.Embed(color=colors.fate)
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
        e.set_author(name=f"Bots Latency", icon_url=self.bot.user.avatar.url)
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
                m = discord.AllowedMentions.none()
                with suppress(Exception):
                    async with aiohttp.ClientSession() as session:
                        webhook = Webhook.from_url(
                            "https://discordapp.com/api/webhooks/673290242819883060/GDXiMBwbzw7dbom57ZupHsiEQ76w8TfV_mEwi7_pGw8CvVFL0LNgwRwk55yRPxNdPA4b",
                            session=session,
                        )
                        files = []
                        for attachment in msg.attachments:
                            if attachment.size > 4000000:
                                return
                            files.append(await attachment.to_file())
                        if msg.author.id == self.bot.user.id:
                            e = discord.Embed(color=colors.fate)
                            e.set_author(
                                name=msg.channel.recipient,
                                icon_url=msg.channel.recipient.avatar.url,
                            )
                            return await webhook.send(
                                username=msg.author.name,
                                avatar_url=msg.author.avatar.url,
                                content=msg.content,
                                files=files,
                                embed=e,
                                allowed_mentions=m
                            )
                        await webhook.send(
                            username=msg.author.name,
                            avatar_url=msg.author.avatar.url,
                            content=msg.content,
                            embeds=msg.embeds,
                            files=files,
                            allowed_mentions=m
                        )


def setup(bot):
    bot.add_cog(Core(bot), override=True)
