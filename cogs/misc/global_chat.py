"""
cogs.misc.global_chat
~~~~~~~~~~~~~

A cog to add functionality for a channel interconnected between multiple others

:copyright: (C) 2020-present Michael Stollings
:license: Proprietary and Confidential, see LICENSE for details
"""

from contextlib import suppress
import asyncio
import json
from os import path
from typing import Union
from datetime import datetime

from discord.ext import commands, tasks
from discord.errors import NotFound, Forbidden
import discord

from botutils import get_prefixes_async, colors


ban_hammers = [
    "https://media1.tenor.com/images/1e46ced92e2521749ca6f72602765c1a/tenor.gif?itemid=18219363"
]
rules = "1. No spamming\n" \
        "2. No NSFW content of any kind\n" \
        "3. No harassment or bullying\n" \
        "4. No content that may trigger epilepsy. This includes emojis\n" \
        "5. No using bot commands in the global channel\n" \
        "6. No advertising of any kind\n" \
        "7. No absurdly long, or spam-ish names\n" \
        "8. Only speak in English\n" \
        "9. Most importantly abide by discords TOS\n" \
        "**Breaking any of these rules results in being blocked from using the channel**"


class GlobalChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.polls = {}
        self.cache = {}
        self.msg_cache = []
        self.msg_chunks = []
        self.cache_task = self.bot.loop.create_task(self.cache_channels())
        self.handle_queue.start()
        self._queue = []
        self.last_id = None
        self.blocked = []
        if path.isfile("data/gcb.json"):
            with open("data/gcb.json") as f:
                self.blocked = json.load(f)

    def cog_unload(self):
        self.handle_queue.cancel()
        if not self.cache_task.done():
            self.cache_task.cancel()

    @property
    def queue(self) -> list:
        self._queue = self._queue[-5:]
        return self._queue

    @tasks.loop(seconds=0.21)
    async def handle_queue(self):
        queued_to_send = []
        sending = list(self.queue)
        if len(sending) > 3 and all(e[2].guild.id == sending[0][2].guild.id for e in sending):
            self.blocked.append(sending[0][2].guild.id)
            await sending[0][2].channel.send("Andddddddd blocked")
            self._queue = []
            return

        for entry in sending:
            if len([e for e in sending if e[2].author.id == entry[2].id]) > 1:
                for e in sending:
                    if e != entry:
                        entry[0].description += f"\nMerged with: {e[0].description}"
                        with suppress(ValueError, NotFound, Forbidden):
                            self._queue.remove(e)
                            await e[2].delete()
                        sending.remove(e)
            if not any(entry[2] in values for values in queued_to_send):
                queued_to_send.append(entry)

        for embed, requires_edit, author_msg in queued_to_send:
            with suppress(ValueError, IndexError):
                self._queue.remove([embed, requires_edit, author_msg])
            if requires_edit:
                for message in self.msg_cache:
                    with suppress(NotFound, Forbidden):
                        await message.edit(embed=embed)
            else:
                self.msg_cache = []
                chunk = {}
                for guild_id, channel in list(self.cache.items()):
                    with suppress(AttributeError):
                        if author_msg.channel.id == channel.id and author_msg.attachments:
                            continue
                    with suppress(NotFound, Forbidden):
                        if channel.permissions_for(channel.guild.me).manage_messages:
                            msg = await channel.send(embed=embed)
                            self.msg_cache.append(msg)
                            chunk[msg.channel.id] = msg.id
                self.msg_chunks.append(chunk)
            with suppress(AttributeError, NotFound, Forbidden):
                if author_msg.attachments:
                    if author_msg.channel.permissions_for(author_msg.guild.me).add_reactions:
                        await author_msg.add_reaction("✅")
                else:
                    await author_msg.delete()

    async def cache_channels(self):
        if not self.bot.is_ready():
            await self.bot.wait_until_ready()
        while True:
            if not self.bot.pool:
                await asyncio.sleep(1)
                continue
            break
        async with self.bot.utils.cursor() as cur:
            await cur.execute(f"select guild_id, channel_id from global_chat;")
            ids = await cur.fetchall()
        for guild_id, channel_id in ids:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                async with self.bot.utils.cursor() as cur:
                    await cur.execute(
                        f"delete from global_chat "
                        f"where guild_id = {guild_id};"
                    )
            else:
                self.cache[guild_id] = channel

    @commands.group(name="gc", aliases=["global-chat", "globalchat", "global_chat"])
    async def _gc(self, ctx):
        if not ctx.invoked_subcommand:
            e = discord.Embed(color=self.bot.config["theme_color"])
            e.set_author(name="Global Chat", icon_url=self.bot.user.avatar.url)
            e.description = "Link a channel into my global channel. " \
                            "Msgs sent into it will be forwarded to other " \
                            "configured channels alongside the same in reverse"
            p = await get_prefixes_async(self.bot, ctx.message)
            p = p[2]  # type: str
            e.add_field(
                name="Usage",
                value=f"{p}gc enable\n"
                      f"{p}gc disable\n"
                      f"{p}gc rules",
                inline=False
            )
            async with self.bot.utils.cursor() as cur:
                await cur.execute("select channel_id from global_chat;")
                channel_count = cur.rowcount
                await cur.execute("select user_id from global_users;")
                user_count = cur.rowcount
            e.set_footer(text=f"{channel_count} Channels | {user_count} Users")
            await ctx.send(embed=e)

    @_gc.command(name="mod")
    @commands.is_owner()
    async def _mod(self, ctx, user: discord.User):
        async with self.bot.utils.cursor() as cur:
            await cur.execute(f"select status from global_users where user_id = {user.id} and status = 'moderator';")
            if cur.rowcount:
                await cur.execute(f"update global_users set status = 'verified' where user_id = {user.id};")
                await ctx.send(f"Removed {user} as a mod")
            else:
                await cur.execute(
                    f"insert into global_users values "
                    f"({user.id}, 'moderator') "
                    f"on duplicate key update "
                    f"status = 'moderator';"
                )
                await ctx.send(f"Added {user} as a mod")

    @_gc.command(name="ban")
    async def _ban(self, ctx, *, target: Union[discord.User, discord.Guild]):
        async with self.bot.utils.cursor() as cur:
            await cur.execute(f"select status from global_users where user_id = {ctx.author.id} and status = 'moderator';")
            if not cur.rowcount:
                return await ctx.send("Only global chat moderators can use this command")
        self.blocked.append(target.id)
        await ctx.send(f"Blocked {target}")

    @_gc.command(name="rules")
    async def rules(self, ctx):
        e = discord.Embed(color=self.bot.config["theme_color"])
        e.description = rules
        await ctx.send(embed=e)

    @_gc.command(name="enable")
    @commands.has_permissions(administrator=True)
    async def _enable(self, ctx):
        msg = await ctx.send("Enabling global chat")
        async with self.bot.utils.cursor() as cur:
            await cur.execute(
                f"insert into global_chat values ("
                f"{ctx.guild.id}, {ctx.channel.id}"
                f") on duplicate key update "
                f"channel_id = {ctx.channel.id};"
            )

        self.cache[ctx.guild.id] = ctx.channel
        await ctx.send("Enabled global chat")

    @_gc.command(name="disable")
    @commands.has_permissions(administrator=True)
    async def _disable(self, ctx):
        async with self.bot.utils.cursor() as cur:
            await cur.execute(f"select * from global_chat where guild_id = {ctx.guild.id};")
            if not cur.rowcount:
                return await ctx.send("Global chat isn't enabled")
            if ctx.guild.id in self.cache:
                del self.cache[ctx.guild.id]
            await cur.execute(f"delete from global_chat where guild_id = {ctx.guild.id};")
        await ctx.send("Disabled global chat")

    @_gc.command(name="verify")
    @commands.cooldown(1, 60, commands.BucketType.user)
    @commands.cooldown(6, 60, commands.BucketType.guild)
    async def verify(self, ctx):
        async with self.bot.utils.cursor() as cur:
            await cur.execute(f"select status from global_users where user_id = {ctx.author.id};")
            if cur.rowcount:
                return await ctx.send("You're already registered")
        channel = self.bot.get_channel(self.bot.config["gc_verify_channel"])
        async for msg in channel.history(limit=15):
            for embed in msg.embeds:
                if str(ctx.author.id) == embed.description:
                    return await ctx.send("You already have an application waiting")

        await ctx.send(
            "Are you aware that the global-chat channel is independent of, and has nothing "
            "to do with the server you're using it in? Reply with `yes` to confirm you understand "
            "its purpose, and won't misuse such purpose. You can reply with `cancel`, or anything else "
            "to stop the verification process"
        )
        reply = await self.bot.utils.get_message(ctx)
        if "yes" not in reply.content.lower():
            return await ctx.send("Alright, stopped the verification process. You can redo at any point in time")

        await ctx.send("What's your reason for wanting access to global chat. Send `cancel` to stop the process")
        reason = await self.bot.utils.get_message(ctx)
        if "cancel" in reason.content:
            with suppress(Forbidden, NotFound):
                await reason.add_reaction("👍")
            return
        if not reason.content:
            return await ctx.send("That's not a valid response. Rerun the command")
        e = discord.Embed(color=self.bot.config["theme_color"])
        e.description = rules
        msg = await ctx.send(
            "Do you agree to **all** of the stated rules in this embed?",
            embed=e
        )
        await msg.add_reaction("👍")
        await msg.add_reaction("👎")
        reaction, _user = await self.bot.utils.get_reaction(ctx)
        if reaction.message.id != msg.id:
            return await ctx.send("Why.. would you do this. Rerun the cmd")
        if str(reaction.emoji) != "👍":
            return await ctx.send("Ok")

        e = discord.Embed(color=self.bot.config["theme_color"])
        e.set_author(name=str(ctx.author), icon_url=ctx.author.avatar.url)
        e.description = str(ctx.author.id)
        e.add_field(name="Reason", value=reason.content)
        e.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon.url)
        msg = await channel.send(embed=e)
        await msg.add_reaction("👍")
        await msg.add_reaction("👎")
        await ctx.send("Sent your application")

    @_gc.command(name="poll")
    async def poll(self, ctx, *, poll):
        active = [m.id for m in list(self.cache.values()) if m]
        if ctx.channel.id not in active:
            return await ctx.send("Global chat isn't active")
        e = discord.Embed()
        e.set_author(name=f"Poll by {ctx.author} 📊", icon_url=ctx.author.avatar.url)
        e.description = poll
        e.set_footer(text="👍 0 | 👎 0")
        self.polls[ctx.author.id] = {
            "messages": [],
            "👍": [],
            "👎": []
        }
        for guild_id, channel in self.cache.items():
            with suppress(NotFound, Forbidden):
                msg = await channel.send(embed=e)
                await msg.add_reaction("👍")
                await msg.add_reaction("👎")
                self.polls[ctx.author.id]["messages"].append(msg)
        self.last_id = None
        with suppress(NotFound, Forbidden):
            await ctx.message.delete()

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if not user.bot and reaction.emoji in ["👍", "👎"]:
            active = [m.id for m in list(self.cache.values()) if m]
            if reaction.message.channel.id in active:
                for user_id, data in list(self.polls.items()):
                    await asyncio.sleep(0)
                    if any(reaction.message.id == m.id for m in data["messages"] if m):
                        if user.id not in data[reaction.emoji]:
                            self.polls[user_id][reaction.emoji].append(user.id)
                            emoji = "👍" if reaction.emoji == "👎" else "👎"
                            if user.id in data[emoji]:
                                self.polls[user_id][emoji].remove(user.id)
                            for message in [m for m in data["messages"] if m and m.embeds]:
                                with suppress(Exception):
                                    e = message.embeds[0]
                                    e.set_footer(text=f"👍 {len(data['👍'])} | 👎 {len(data['👎'])}")
                                    await message.edit(embed=e)
                        with suppress(Exception):
                            await reaction.message.remove_reaction(reaction.emoji, user)

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.content.startswith("."):
            return
        active = [m.id for m in list(self.cache.values()) if m]
        if not msg.author.bot and msg.channel.id in active:
            # Duplicate messages
            if msg.content and any(msg.content == m.content for m in self.msg_cache):
                return
            if msg.guild.id in self.blocked or msg.author.id in self.blocked:
                return

            # Missing permissions to moderate global chat
            perms = msg.channel.permissions_for(msg.guild.me)
            if not perms.send_messages or not perms.embed_links or not perms.manage_messages:
                async with self.bot.utils.cursor() as cur:
                    await cur.execute(f"delete from global_chat where guild_id = {msg.guild.id};")
                del self.cache[msg.guild.id]
                with suppress(Exception):
                    return await msg.channel.send(
                        "Disabled global chat due to missing permissions"
                    )

            async with self.bot.utils.cursor() as cur:
                await cur.execute(f"select status from global_users where user_id = {msg.author.id};")
                if not cur.rowcount:
                    return await msg.channel.send("You're not verified into using this channel. Run `.gc verify` in a different channel")
                await cur.execute(
                    f"select status from global_users "
                    f"where user_id = {msg.author.id} "
                    f"and status = 'blocked';"
                )
                if cur.rowcount:
                    return await msg.channel.send("You're blocked from using global chat")
                await cur.execute(
                    f"select status from global_users "
                    f"where user_id = {msg.author.id} "
                    f"and status = 'moderator';"
                )
                mod = False
                if cur.rowcount:
                    mod = True

                # Update the last use for this server
                await cur.execute(
                    f"insert into global_activity values ("
                    f"{msg.guild.id}, '{str(datetime.now())}') "
                    f"on duplicate key update "
                    f"last_used = '{str(datetime.now())}';"
                )

            if not mod:
                abcs = "abcdefghijklmnopqrstuvwxyz"
                for i, char in enumerate(list(msg.content)):
                    await asyncio.sleep(0)
                    if char == "." and i != 0 and i + 1 != len(msg.content):
                        l = msg.content[i - 1]
                        r = msg.content[i + 1]
                        if l and l in abcs and r and r in abcs:
                            return await msg.channel.send("No links..")

            e = discord.Embed(color=msg.author.color)
            e.set_thumbnail(url=msg.guild.icon.url)
            author = str(msg.author)
            if mod:
                author += " 👮‍♂️"
            e.set_author(name=author, icon_url=msg.author.avatar.url)

            # Convert mentions to nicknames so everyone can read them
            ctx = await self.bot.get_context(msg)
            converter = commands.clean_content(use_nicknames=True)
            msg.content = await converter.convert(ctx, msg.content)

            # The fact that I have to do this is sad
            if "balls" in msg.content.lower() or "ba11s" in msg.content.lower() or "bals" in msg.content.lower():
                msg.content = msg.content.lower()\
                    .replace("balls", "<:milk:814928895316852756>")\
                    .replace("ba11s", "<:milk:814928895316852756>")\
                    .replace("bals", "<:milk:814928895316852756>")

            # Edit & combine their last msg
            if msg.author.id == self.last_id and self.msg_cache:
                em = self.msg_cache[0].embeds[0]
                if str(msg.author) in em.author.name and not isinstance(e.image.url, str):
                    if msg.attachments:
                        em.set_image(url=msg.attachments[0].url)
                    if em.description:
                        em.description += f"\n{msg.content[:256]}"
                    elif msg.content:
                        em.description = f"{msg.content[:256]}"
                    if len(em.description) >= 1048:
                        return
                    self._queue.append([em, True, msg])
                    return

            # Send a new msg
            if msg.attachments:
                e.set_image(url=msg.attachments[0].url)
            e.set_thumbnail(url=msg.guild.icon.url)
            e.description = msg.content[:512]
            self._queue.append([e, False, msg])
            if msg.attachments:
                self.last_id = None
            else:
                self.last_id = msg.author.id

    @commands.Cog.listener()
    async def on_message_delete(self, msg):
        if msg.channel.id == 709035348629520425:
            for chunk in list(self.msg_chunks):
                if msg.id in chunk.values():
                    for channel_id, msg_id in chunk.items():
                        channel = self.bot.get_channel(channel_id)
                        with suppress(NotFound, Forbidden):
                            m = await channel.fetch_message(msg_id)
                            await m.delete()
                    return

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.channel_id == self.bot.config["gc_verify_channel"]:
            if payload.user_id == self.bot.user.id:
                return
            channel = self.bot.get_channel(payload.channel_id)
            msg = await channel.fetch_message(payload.message_id)
            if not msg.embeds[0].description.isdigit():
                return
            user_id = int(msg.embeds[0].description)

            user = await self.bot.fetch_user(user_id)
            e = discord.Embed(color=colors.green)
            if str(payload.emoji) == "👍":
                async with self.bot.utils.cursor() as cur:
                    await cur.execute(f"insert into global_users values ({user_id}, 'verified');")
                e.set_author(name=f"{user} was verified", icon_url=user.avatar.url)
                self._queue.append([e, False, msg])
                self.last_id = None
            else:
                with suppress(NotFound, Forbidden):
                    await user.send("Your verification into global-chat was denied.")
                await msg.delete()


def setup(bot):
    bot.add_cog(GlobalChat(bot), override=True)
