"""
cogs.moderation.chatfilter
~~~~~~~~~~~~~~~~~~~~~~~~~~~

A cog for filtering out messages containing filtered words

:copyright: (C) 2020-present FrequencyX4, All Rights Reserved
:license: Proprietary, see LICENSE for details
"""

import re
from time import time
import asyncio
from contextlib import suppress
from unicodedata import normalize
from string import printable
import os
from typing import *

from discord.ext import commands
import discord
from discord.errors import NotFound, Forbidden
from discord import ui, ButtonStyle, Message, Member

from botutils import colors, split, CancelButton, findall, GetChoice
from cogs.moderation.logger import Log


aliases = {
    "a": ["@"],
    "i": ['1', 'l', r'\|', "!", "/", r"\*", ";"],
    "o": ["0", "@", "ø", "о"],
    "x": ["х"],
    "y": ["у"]
}
lang_aliases = {
    "x": ["х"],
    "y": ["у"]
}
esc = "\\"


presets = {
    "All Links (Needs Regex Enabled)": [
        "((https?://)|(www\.)|(discord\.gg/))[a-zA-Z0-9./]+"
    ],
    "Advertising Links": [
        "youtube.com", "youtu.be", "discord.gg", "invite.gg", "discord.invite", "discord.com"
    ],
    "Offensive Slurs": [
        "nigger", "nigga", "fag", "faggot", "spic", "coon", "chink", "trasvesite", "tranny"
    ]
}



class ChatFilter(commands.Cog):
    webhooks: Dict[str, discord.Webhook] = {}

    def __init__(self, bot):
        if not hasattr(bot, "filtered_messages"):
            bot.filtered_messages = {}
        self.bot = bot
        self.config = bot.utils.cache("chatfilter")
        self.chatfilter_usage = self._chatfilter

    def is_enabled(self, guild_id: int) -> bool:
        """ Denotes whether or not the modules enabled in a specific guild """
        return guild_id in self.config

    async def clean_content(self, content: str, flag: str) -> str:
        """ Sanitizes content to be resent with the flag filtered out """
        flag = flag.rstrip(" ")
        for chunk in content.split():
            if flag.lower() in chunk.lower():
                filtered_word = f"{flag[0]}{f'{esc}*' * (len(chunk) - 1)}"
                content = content.lower().replace(chunk.lower(), filtered_word.lower())
        for line in content.split("\n"):
            for _ in range(50):
                await asyncio.sleep(0)
                if content.count(line) > 1:
                    content = content.replace(line + line, line)
                else:
                    break
        return content

    async def run_default_filter(self, guild_id: int, content: str) -> Tuple[Optional[str], Optional[list]]:
        """ Filters the content of a message without using regex to prevent false flags """
        if guild_id not in self.config:
            return None, None
        content = "".join(c for c in content if c in printable)
        content = normalize('NFKD', content).encode('ascii', 'ignore').decode()
        for letter, alts in lang_aliases.items():
            await asyncio.sleep(0)
            for alias in alts:
                content = content.replace(alias, letter)
        if results := await findall(" +[a-zA-Z] +", content):
            for result in results:
                await asyncio.sleep(0)
                content = content.replace(result, result.replace(result, result.strip()))
        for phrase in self.config[guild_id]["blacklist"]:
            await asyncio.sleep(0)
            if esc in content:
                content = content.replace("\\", "")
            if " " in phrase and phrase.lower() in content.lower():
                return await self.clean_content(content, phrase), [phrase]
            for word in content.lower().replace("\n", "").split():
                await asyncio.sleep(0)
                if phrase in word and word not in self.config[guild_id]["whitelist"]:
                    return await self.clean_content(content, phrase), [phrase]
        return None, None

    async def run_regex_filter(self, guild_id: int, content: str) -> Tuple[Optional[str], Optional[list]]:
        """ A more thorough filter to better flag bypasses """
        if guild_id not in self.config:
            return None, None

        def run_regex() -> Optional[str]:
            result = re.search(query, content.replace(" ", ""))
            if result:
                return result.group()
            return None

        illegal = ("\\", "`", "__", "||", "~~")
        content = str(content).lower()
        for char in illegal:
            content = content.replace(char, "")
        content = normalize('NFKD', content).encode('ascii', 'ignore').decode()
        content = "".join(c for c in content if c in printable)

        flags = []
        for word in self.config[guild_id]["blacklist"]:
            await asyncio.sleep(0)

            # Sanitize the query
            query = word.replace("*", "{0,16}").replace("+", "{1,16}").replace("\n", "")
            ranges = await findall("{[0-9]+, ?[0-9]+}", query)
            for match in ranges:
                await asyncio.sleep(0)
                num = match.strip("{}").split(f",{' ' if ' ' in match else ''}")
                if int(num[1]) > 16:
                    query = query.replace(match, "{" + num[0] + ",16}")

            try:
                before = time()
                if result := await self.bot.loop.run_in_executor(None, run_regex):
                    for word in content.split():
                        await asyncio.sleep(0)
                        if result in word and word not in self.config[guild_id]["whitelist"]:
                            flags.append(result)
                            break
                if time() - before > 3:
                    self.bot.log.critical(f"Removing bad regex: {word}")
                    with suppress(ValueError):
                        self.config[guild_id]["blacklist"].remove(word)
            except re.error:
                with suppress(ValueError):
                    self.config[guild_id]["blacklist"].remove(word)

        if not flags:
            return None, flags

        for flag in flags:
            content = await self.clean_content(content, flag)

        return content, flags

    @commands.group(name="chatfilter", description="Shows how to configure the module")
    @commands.bot_has_permissions(embed_links=True)
    async def _chatfilter(self, ctx):
        if not ctx.invoked_subcommand:
            guild_id = ctx.guild.id
            toggle = "disabled"
            if ctx.guild.id in self.config and self.config[guild_id]["toggle"]:
                toggle = "enabled"
            e = discord.Embed(color=colors.pink)
            e.set_author(name="| Chat Filter", icon_url=ctx.author.display_avatar.url)
            if ctx.guild.icon:
                e.set_thumbnail(url=ctx.guild.icon.url)
            e.description = "Deletes messages containing blocked words/phrases. " \
                            "You can add multiple via something like `word1, word2`. If " \
                            "you use regex, note that high ranges like * + or {1,1000} are " \
                            "replaced with either {0,16} or {1,16}"
            e.add_field(
                name="◈ Usage",
                value="**.chatfilter ignore #channel**\n"
                      "**.chatfilter unignore #channel**\n"
                      "**.chatfilter add [word/phrase]**\n"
                      "**.chatfilter remove [word/phrase]**\n"
                      "**.chatfilter whitelist [word/phrase]**\n"
                      "**.chatfilter unwhitelist [word/phrase]**",
                inline=False,
            )
            if guild_id in self.config and self.config[guild_id]["ignored"]:
                channels = []
                for channel_id in list(self.config[guild_id]["ignored"]):
                    channel = self.bot.get_channel(channel_id)
                    if not channel:
                        self.config[guild_id]["ignored"].remove(channel_id)
                        await self.config.flush()
                        continue
                    channels.append(channel.mention)
                if channels:
                    e.add_field(name="◈ Ignored Channels", value="\n".join(channels))
            e.set_footer(text=f"Current Status: {toggle}")
            view = Menu(self, ctx)
            msg = await ctx.send(embed=e, view=view)
            await view.wait()
            for button in view.children:
                button.disabled = True
            await msg.edit(view=view)

    @_chatfilter.command(name="enable", description="Enables the module")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def _enable(self, ctx):
        if ctx.guild.id in self.config and self.config[ctx.guild.id]["toggle"]:
            return await ctx.send("Chatfilter is already enabled")
        if ctx.guild.id in self.config:
            self.config[ctx.guild.id]["toggle"] = True
        else:
            self.config[ctx.guild.id] = {
                "toggle": True,
                "blacklist": [],
                "whitelist": [],
                "ignored": []
            }
        if ctx.command.name.lower() == "enable":
            await ctx.send("Enabled chatfilter")
        await self.config.flush()

    @_chatfilter.command(name="disable", description="Disables the module")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def _disable(self, ctx):
        if ctx.guild.id not in self.config:
            return await ctx.send("Chatfilter is not enabled")
        self.config[ctx.guild.id]["toggle"] = False
        if ctx.command.name.lower() == "disable":
            await ctx.send("Disabled chatfilter")
        await self.config.flush()

    @_chatfilter.command(name="ignore", description="Has chatfilter ignore a channel")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def _ignore(self, ctx, *channels: discord.TextChannel):
        guild_id = ctx.guild.id
        if guild_id not in self.config:
            return await ctx.send("Chatfilter isn't enabled")
        passed = []
        for channel in channels:
            if channel.id in self.config[guild_id]["ignored"]:
                await ctx.send(f"{channel.mention} is already ignored")
                continue
            self.config[guild_id]["ignored"].append(channel.id)
            passed.append(channel.mention)
        if passed:
            await ctx.send(f"I'll now ignore {', '.join(passed)}")
            await self.config.flush()

    @_chatfilter.command(name="unignore", description="Disables ignoring a channel")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def _unignore(self, ctx, *channels: discord.TextChannel):
        guild_id = ctx.guild.id
        if guild_id not in self.config:
            return await ctx.send("This server has no ignored channels")
        passed = []
        for channel in channels:
            if channel.id not in self.config[guild_id]["ignored"]:
                await ctx.send(f"{channel.mention} isn't ignored")
                continue
            self.config[guild_id]["ignored"].remove(channel.id)
            passed.append(channel.mention)
        if passed:
            await ctx.send(f"I'll no longer ignore {', '.join(passed)}")
            await self.config.flush()

    @_chatfilter.command(name="add", aliases=["blacklist"], description="Adds a word, or phrase to the filter")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def _add(self, ctx, *, phrases):
        guild_id = ctx.guild.id
        if guild_id not in self.config:
            return await ctx.send("Chatfilter isn't enabled")
        if len(phrases) > 256:
            return await ctx.send("That's too large to add")
        for phrase in phrases.split(", ")[:16]:
            if len(phrase) > 64:
                return await ctx.send("That's too large to add")
            if phrase in self.config[guild_id]["blacklist"]:
                await ctx.send(f"`{phrase}` is already blacklisted")
            self.config[guild_id]["blacklist"].append(phrase)
            await ctx.send(f"Added `{phrase}`")
            await asyncio.sleep(1)
        await self.config.flush()

    @_chatfilter.command(name="whitelist", description="Adds a word, or phrase to the whitelist")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def _whitelist(self, ctx, *, phrases):
        guild_id = ctx.guild.id
        if guild_id not in self.config:
            return await ctx.send("Chatfilter isn't enabled")
        if len(phrases) > 256:
            return await ctx.send("That's too large to add")
        for phrase in phrases.split(", ")[:16]:
            if len(phrase) > 64:
                return await ctx.send("That's too large to add")
            if phrase in self.config[guild_id]["whitelist"]:
                await ctx.send(f"`{phrase}` is already whitelisted")
            self.config[guild_id]["whitelist"].append(phrase)
            await ctx.send(f"Added `{phrase}`")
            await asyncio.sleep(1)
        await self.config.flush()

    @_chatfilter.command(name="unwhitelist", description="Removes a word, or phrase from the whitelist")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def _unwhitelist(self, ctx, *, phrases):
        guild_id = ctx.guild.id
        if guild_id not in self.config:
            return await ctx.send("Chatfilter isn't enabled")
        if len(phrases) > 256:
            return await ctx.send("That's too large to add")
        for phrase in phrases.split(", ")[:16]:
            if len(phrase) > 64:
                return await ctx.send("That's too large to add")
            if phrase not in self.config[guild_id]["whitelist"]:
                return await ctx.send(f"`{phrase}` isn't whitelisted")
            self.config[guild_id]["whitelist"].remove(phrase)
            await ctx.send(f"Removed `{phrase}`")
            await asyncio.sleep(1)
        await self.config.flush()

    @_chatfilter.command(name="remove", description="Removes a word, or phrase from the filter")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def _remove(self, ctx, *, phrase):
        guild_id = ctx.guild.id
        if guild_id not in self.config:
            return await ctx.send("Chatfilter isn't enabled")
        if phrase not in self.config[guild_id]["blacklist"] and not phrase.endswith("*") and not phrase.startswith("*"):
            return await ctx.send("Phrase/word not found")
        removed = []
        if phrase.endswith("*"):
            phrase = phrase.rstrip("*")
            for word in list(self.config[guild_id]["blacklist"]):
                _word = normalize('NFKD', word).encode('ascii', 'ignore').decode().lower()
                if _word.startswith(phrase):
                    self.config[guild_id]["blacklist"].remove(word)
                    removed.append(word)
            if not removed:
                return await ctx.send("No phrase/words found matching that")
            await ctx.send(f"Removed {', '.join(f'`{w}`' for w in removed)}")
            return await self.config.flush()
        if phrase.startswith("*"):
            print("Bruh")
            phrase = phrase.lstrip("*")
            for word in list(self.config[guild_id]["blacklist"]):
                print(word)
                _word = normalize('NFKD', word).encode('ascii', 'ignore').decode().lower()
                if _word.endswith(phrase):
                    self.config[guild_id]["blacklist"].remove(word)
                    removed.append(word)
            if not removed:
                return await ctx.send("No phrase/words found matching that")
            await ctx.send(f"Removed {', '.join(f'`{w}`' for w in removed)}")
            return await self.config.flush()
        self.config[guild_id]["blacklist"].remove(phrase)
        await ctx.send(f"Removed `{phrase}`")
        await self.config.flush()

    @_chatfilter.command(name="sanitize", description="Filters old/existing messages")
    @commands.cooldown(1, 120, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 60, commands.BucketType.guild)
    async def sanitize(self, ctx, amount: int):
        """ Clean up existing chat history """
        view = CancelButton("manage_messages")
        message = await ctx.send("🖨️ **Sanitizing chat history**", view=view)
        if amount > 1000 and ctx.author.id not in self.bot.owner_ids:
            amount = 1000

        # Create a listener to let the code know if the original message was deleted
        task: asyncio.Task = self.bot.loop.create_task(self.bot.wait_for(
            "message_delete",
            check=lambda m: m.id == message.id,
            timeout=900
        ))

        method = self.run_default_filter
        if self.config[ctx.guild.id]["regex"]:
            method = self.run_regex_filter

        # Status variables
        scanned = 0
        deleted = []
        last_update = time()
        last_user = None

        async for msg in message.channel.history(limit=amount):
            await asyncio.sleep(0)
            if view.is_cancelled or not message or task.done():
                return
            scanned += 1

            # Check for flags
            _content, flags = await method(ctx.guild.id, msg.content)
            if flags:
                with suppress(NotFound, Forbidden):
                    await msg.delete()
                    date = msg.created_at.strftime("%m/%d/%Y %I:%M:%S%p")
                    newline = "" if last_user == msg.author.id else "\n"
                    deleted.append(f"{newline}{date} - {msg.author} - {msg.content}")
                    last_user = msg.author.id
                    break

            # Update the message every 5 seconds
            if time() - 5 > last_update:
                await message.edit(
                    content=f"🖨️ **Sanitizing chat history**\n"
                            f"{scanned} messages scanned\n"
                            f"{len(deleted)} messages deleted"
                )
                last_update = time()

        try:
            # Stop listening for button presses after scanning channel history
            view.stop()
            task.cancel()
            await message.edit(
                content=message.content.replace("Sanitizing", "Sanitized"),
                view=None
            )

            # Send the deleted messages as a txt
            async with self.bot.utils.open("./static/messages.txt", "w") as f:
                await f.write("\n".join(deleted))
            await ctx.send(
                "Operation finished, this attachment will be deleted in a minute",
                reference=message,
                file=discord.File("./static/messages.txt"),
                delete_after=60
            )
            with suppress(Exception):
                os.remove("./static/messages.txt")
        except (discord.errors.HTTPException, NotFound):
            await ctx.send("The message I was using got deleted, so I can't proceed")

    async def get_webhook(self, channel):
        if channel.id not in self.webhooks:
            webhooks = await channel.webhooks()
            for wh in webhooks:
                if wh.name == "Chatfilter":
                    webhook = wh
                    break
            else:
                webhook = await channel.create_webhook(name="Chatfilter")
            if channel.id not in self.webhooks:
                self.webhooks[channel.id] = webhook
            else:
                await webhook.delete()
                return self.webhooks[channel.id]
        return self.webhooks[channel.id]

    def log_action(self, msg: Message, flags: List[str]) -> None:
        e = discord.Embed(color=colors.white)
        e.set_author(name="~==🍸msg Filtered🍸==~")
        e.description = self.bot.utils.format_dict({
            "Author": str(msg.author),
            "Mention": msg.author.mention,
            "ID": str(msg.author.id),
            "Flags": ", ".join(flags)
        })
        for chunk in split(msg.content, 1024):
            e.add_field(
                name="◈ Content",
                value=chunk,
                inline=False
            )
        try:
            cog = self.bot.cogs["Logger"]
            log = Log("chat_filter", embed=e)
            cog.put_nowait(str(msg.guild.id), log)
        except KeyError:
            return

    @commands.Cog.listener()
    async def on_message(self, msg: Message) -> None:
        if hasattr(msg.guild, "id") and msg.guild.id in self.config:
            await asyncio.sleep(0.21)
            guild_id = msg.guild.id
            if not self.config[guild_id]["toggle"]:
                return
            if str(msg.author).endswith("#0000"):
                return
            if self.bot.attrs.is_moderator(msg.author) and not msg.author.bot:
                return
            if msg.author.bot and "bots" not in self.config[guild_id]:
                return
            if msg.channel.id in self.config[guild_id]["ignored"]:
                return
            if "regex" in self.config[guild_id]:
                result, flags = await self.run_regex_filter(guild_id, msg.content)
            else:
                result, flags = await self.run_default_filter(guild_id, msg.content)
            if not result:
                return
            with suppress(Exception):
                await msg.delete()

                # Mark a message_id as a filtered message
                if guild_id not in self.bot.filtered_messages:
                    self.bot.filtered_messages[guild_id] = {}
                self.bot.filtered_messages[guild_id][msg.id] = time()

                # Tell the logger module that a message was deleted by chatfilter
                self.log_action(msg, flags)

                # Resend the message, but with the filtered word, or phrase removed
                if self.config[guild_id]["webhooks"]:
                    if msg.channel.permissions_for(msg.guild.me).manage_webhooks:
                        w = await self.get_webhook(msg.channel)
                        await w.send(
                            content=result,
                            avatar_url=msg.author.display_avatar.url,
                            username=msg.author.display_name
                        )

                # Check their nickname for filtered content
                await self.on_member_update(None, msg.author)

    @commands.Cog.listener()
    async def on_message_edit(self, _before: Message, after: Message) -> None:
        """ Check edited messages for added filtered words, or phrases """
        await self.on_message(after)

    @commands.Cog.listener()
    async def on_member_update(self, _before: Optional[Member], after: Member) -> None:
        """ Resets a members nickname if it has a filtered word, or phrase """
        if after.nick and hasattr(after.guild, "id") and after.guild.id in self.config:
            guild_id = after.guild.id
            if not self.config[guild_id]["toggle"]:
                return
            if self.bot.attrs.is_moderator(after) and not after.bot:
                return
            if after.bot and "bots" not in self.config[guild_id]:
                return
            if "regex" in self.config[guild_id]:
                result, flags = await self.run_regex_filter(guild_id, after.nick)
            else:
                result, flags = await self.run_default_filter(guild_id, after.nick)
            if not result:
                return
            await after.edit(nick=None, reason=f"Chatfilter flagged their nick for '{', '.join(flags)}'")


style = ButtonStyle


class Menu(ui.View):
    def __init__(self, cls: ChatFilter, ctx: commands.Context) -> None:
        self.cls = cls
        self.ctx = ctx
        self.extra: Dict[str, discord.Button] = {}
        self.cd1 = cls.bot.utils.cooldown_manager(3, 25)
        self.cd2 = cls.bot.utils.cooldown_manager(2, 5)
        self.configuring = False
        super().__init__(timeout=60)

        if ctx.guild.id in cls.config:
            if cls.config[ctx.guild.id]["toggle"]:
                self.update_items()

    async def on_error(self, error: Exception, _item, _interaction) -> None:
        """ Suppress NotFound errors as they're spammy """
        if not isinstance(error, NotFound):
            raise error

    async def import_callback(self, interaction):
        """ Import existing configs """
        user = interaction.guild.get_member(interaction.user.id)
        check1 = self.cd1.check(interaction.user.id)
        check2 = self.cd2.check(interaction.user.id)
        if check1 or check2:
            return await interaction.response.send_message(
                "You're on cooldown, try again in a moment", ephemeral=True
            )
        if not user.guild_permissions.manage_messages:
            return await interaction.response.send_message(
                f"You need manage_message permissions to toggle this", ephemeral=True
            )
        view = ImportView(self.cls, self.ctx)
        await interaction.response.send_message("Choose what to import", view=view, ephemeral=True)

    def update_items(self) -> None:
        """ Updates the color of extra config options to reflect being enabled or disabled """
        guild_id = self.ctx.guild.id
        if not self.configuring:
            for custom_id, button in self.extra.items():
                button.disabled = True
        else:
            toggle = guild_id in self.cls.config and self.cls.config[guild_id]["toggle"]
            color = style.red if toggle else style.green
            if "toggle" not in self.extra:
                button = ui.Button(label="Disable" if toggle else "Enable", style=color)
                button.callback = self.toggle
                self.add_item(button)
                self.extra["toggle"] = button

            if not toggle:
                for name, button in self.extra.items():
                    if name != "toggle":
                        button.disabled = True
                return

            conf = self.cls.config[guild_id]
            for button in self.extra.values():
                button.disabled = False

            color = style.green if "filter_nicks" in conf else style.red
            if "filter_nicks" in self.extra:
                self.extra["filter_nicks"].style = color
            else:
                button = ui.Button(label="Filter Nicks", style=color, custom_id="filter_nicks")
                button.callback = self.handle_callback
                self.add_item(button)
                self.extra["filter_nicks"] = button

            color = style.green if "bots" in conf else style.red
            if "bots" in self.extra:
                self.extra["bots"].style = color
            else:
                button = ui.Button(label="Filter Bots", style=color, custom_id="bots")
                button.callback = self.handle_callback
                self.add_item(button)
                self.extra["bots"] = button

            color = style.green if "webhooks" in conf else style.red
            if "webhooks" in self.extra:
                self.extra["webhooks"].style = color
            else:
                button = ui.Button(label="Use Webhooks", style=color, custom_id="webhooks")
                button.callback = self.handle_callback
                self.add_item(button)
                self.extra["webhooks"] = button

            color = style.green if "regex" in conf else style.red
            if "regex" in self.extra:
                self.extra["regex"].style = color
            else:
                button = ui.Button(label="Use Regex", style=color, custom_id="regex")
                button.callback = self.handle_callback
                self.add_item(button)
                self.extra["regex"] = button

            if "import" not in self.extra:
                button = ui.Button(label="Import Words", style=style.blurple)
                button.callback = self.import_callback
                self.add_item(button)
                self.extra["import"] = button

    async def handle_callback(self, interaction: discord.Interaction) -> object:
        """ Handles the interactions from sub module toggles """
        user = interaction.guild.get_member(interaction.user.id)
        check1 = self.cd1.check(interaction.user.id)
        check2 = self.cd2.check(interaction.user.id)
        if check1 or check2:
            return await interaction.response.send_message(
                "You're on cooldown, try again in a moment", ephemeral=True
            )
        if not user.guild_permissions.manage_messages:
            return await interaction.response.send_message(
                f"You need manage_message permissions to toggle this", ephemeral=True
            )
        custom_id = interaction.data["custom_id"]
        if self.extra[custom_id].style is style.blurple:
            return await interaction.response.send_message(
                f"Enable chatfilter to toggle this", ephemeral=True
            )
        if custom_id in self.cls.config[self.ctx.guild.id]:
            await self.cls.config.remove_sub(self.ctx.guild.id, custom_id)
        else:
            self.cls.config[self.ctx.guild.id][custom_id] = True
            await self.cls.config.flush()
        self.update_items()
        toggle = "Enabled" if self.extra[custom_id].style is style.green else "Disabled"
        if custom_id == "filter_nicks":
            m = f"{toggle} filtering members nicknames"
        elif custom_id == "bots":
            m = f"{toggle} filtering bot messages"
        elif custom_id == "webhooks":
            m = f"{toggle} resending deleted messages with the content filtered"
        else:
            m = f"{toggle} the use of regex. This improves sensitivity, but can falsely flag"
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(m, ephemeral=True)

    @ui.button(label="Filtered Words", style=style.blurple)
    async def filtered_words(self, _button, interaction):
        """ Sends the current list of filtered words """
        filtered = ""
        if self.ctx.guild.id in self.cls.config:
            filtered = "**,** ".join(self.cls.config[self.ctx.guild.id]["blacklist"])
        with suppress(Exception):
            await interaction.response.send_message(
                f"**Filtered words:** {filtered}", ephemeral=True
            )

    @ui.button(label="Configure", style=style.blurple)
    async def configure(self, button, interaction):
        """ Adds the config related buttons to the view """
        user = interaction.guild.get_member(interaction.user.id)
        if not user.guild_permissions.manage_messages:
            return await interaction.response.send_message(
                f"You need manage_message permissions to toggle this", ephemeral=True
            )
        self.remove_item(button)
        self.configuring = True
        self.update_items()
        await interaction.response.edit_message(view=self)

    async def toggle(self, interaction: discord.Interaction):
        """ Toggle the chatfilter module as a whole """
        user = interaction.guild.get_member(interaction.user.id)
        check1 = self.cd1.check(interaction.user.id)
        check2 = self.cd2.check(interaction.user.id)
        if check1 or check2:
            return await interaction.response.send_message(
                "You're on cooldown, try again in a moment", ephemeral=True
            )
        if not user.guild_permissions.manage_messages:
            return await interaction.response.send_message(
                f"You need manage_message permissions to toggle this", ephemeral=True
            )
        button = self.extra["toggle"]
        if button.label == "Enable":
            await self.cls._enable(self.ctx)  # type: ignore
            button.style = style.red
            button.label = "Disable"
        else:
            await self.cls._disable(self.ctx)  # type: ignore
            button.style = style.green
            button.label = "Enable"
        self.update_items()
        await interaction.response.defer()
        await interaction.message.edit(view=self)


class ImportView(ui.View):
    def __init__(self, cls: ChatFilter, ctx: commands.Context):
        self.cls = cls
        self.ctx = ctx
        super().__init__(timeout=45)

    async def on_error(self, error, item, interaction) -> None:
        if not isinstance(error, NotFound):
            raise

    @ui.button(label="From Preset", style=style.blurple)
    async def load_from_preset(self, _button, interaction):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message(
                "Only the user who initiated this command can interact",
                ephemeral=True
            )
        await interaction.response.defer(ephemeral=True)
        choice = await GetChoice(self.ctx, presets.keys())
        added = []
        for phrase in presets[choice]:
            if phrase not in self.cls.config[interaction.guild.id]["blacklist"]:
                self.cls.config[interaction.guild.id]["blacklist"].append(phrase)
                added.append(phrase)
        added = [
            f"`{phrase}`" for phrase in added
        ]
        await interaction.followup.send(f"**Imported:** {', '.join(added)}", ephemeral=True)
        self.stop()

    @ui.button(label="From Another Server", style=style.blurple)
    async def load_from_server(self, _button, interaction):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message(
                "Only the user who initiated this command can interact",
                ephemeral=True
            )
        options = {
            g.name: g.id for g in interaction.user.mutual_guilds
            if g.id in self.cls.config
        }
        await interaction.response.defer(ephemeral=True)
        choice = await GetChoice(self.ctx, options.keys())
        guild_id = options[choice]
        added = []
        for phrase in self.cls.config[guild_id]["blacklist"]:
            await asyncio.sleep(0)
            if phrase not in self.cls.config[interaction.guild.id]["blacklist"]:
                self.cls.config[interaction.guild.id]["blacklist"].append(phrase)
                added.append(phrase)
        added = [
            f"`{discord.utils.escape_markdown(phrase)}`"
            for phrase in added
        ]
        await interaction.followup.send(f"**Imported:** {', '.join(added)}", ephemeral=True)
        self.stop()


def setup(bot):
    bot.add_cog(ChatFilter(bot), override=True)
