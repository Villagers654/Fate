import re
from discord.ext import commands
from botutils import colors
import discord
import asyncio
from contextlib import suppress


aliases = {
    "i": ['1', 'l', r'\|'],
    "o": ["0", "@"]
}


class ChatFilter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = bot.utils.cache("chatfilter")
        self.chatfilter_usage = self._chatfilter

    async def filter(self, content: str, filtered_words: list):
        def run_regex():
            regexes = []
            for word in filtered_words:
                fmt = word.lower()
                for letter, _aliases in aliases.items():
                    regex = f"({letter + '|' + '|'.join(_aliases)})"
                    fmt = fmt.replace(letter, regex)
                regexes.append(fmt)

            for regex in regexes:
                result = re.search(regex, content)
                if result:
                    return f"Got flagged for {result.group()}"
            return "Didn't get flagged"

        content = str(content).lower()
        return await self.bot.loop.run_in_executor(None, run_regex)

    @commands.command(name="test-filter")
    @commands.is_owner()
    async def test_filter(self, ctx, *, content):
        filter = [
            "fuck",
            "shit",
            "some"
        ]
        result = await self.filter(content, filter)
        return await ctx.send(result)

    @commands.group(name="chatfilter")
    @commands.bot_has_permissions(embed_links=True)
    async def _chatfilter(self, ctx):
        if not ctx.invoked_subcommand:
            guild_id = ctx.guild.id
            toggle = "disabled"
            if ctx.guild.id in self.config and self.config[guild_id]["toggle"]:
                toggle = "enabled"
            e = discord.Embed(color=colors.pink())
            e.set_author(name="| Chat Filter", icon_url=ctx.author.avatar_url)
            e.set_thumbnail(url=ctx.guild.icon_url)
            e.description = "Deletes messages containing blocked words/phrases"
            e.add_field(
                name="◈ Usage",
                value=".chatfilter enable\n"
                ".chatfilter disable\n"
                ".chatfilter ignore #channel\n"
                ".chatfilter unignore #channel\n"
                ".chatfilter add {word/phrase}\n"
                ".chatfilter remove {word/phrase}\n"
                ".chatfilter toggle-bots\n"
                "`whether to filter bot messages`",
                inline=False,
            )
            if guild_id in self.config and self.config[guild_id]["blacklist"]:
                text = str(self.config[guild_id]["blacklist"])
                for text_group in [
                    text[i : i + 1000] for i in range(0, len(text), 1000)
                ]:
                    e.add_field(name="◈ Blacklisted Words/Phrases", value=text_group, inline=False)
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
            await ctx.send(embed=e)

    @_chatfilter.command(name="enable")
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
                "ignored": []
            }
        await ctx.send("Enabled chatfilter")
        await self.config.flush()

    @_chatfilter.command(name="disable")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def _disable(self, ctx):
        if ctx.guild.id not in self.config:
            return await ctx.send("Chatfilter is not enabled")
        self.config[ctx.guild.id]["toggle"] = False
        await ctx.send("Disabled chatfilter")
        await self.config.flush()

    @_chatfilter.command(name="ignore")
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

    @_chatfilter.command(name="unignore")
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

    @_chatfilter.command(name="add")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def _add(self, ctx, *, phrase):
        guild_id = ctx.guild.id
        if guild_id not in self.config:
            return await ctx.send("Chatfilter isn't enabled")
        if phrase in self.config[guild_id]["blacklist"]:
            return await ctx.send("That word/phrase is already blacklisted")
        self.config[guild_id]["blacklist"].append(phrase)
        await ctx.send(f"Added `{phrase}`")
        await self.config.flush()

    @_chatfilter.command(name="remove")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def _remove(self, ctx, *, phrase):
        guild_id = ctx.guild.id
        if guild_id not in self.config:
            return await ctx.send("Chatfilter isn't enabled")
        if phrase not in self.config[guild_id]["blacklist"]:
            return await ctx.send("Phrase/word not found")
        self.config[guild_id]["blacklist"].remove(phrase)
        await ctx.send(f"Removed `{phrase}`")
        await self.config.flush()

    @_chatfilter.command(name="toggle-bots")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def toggle_bots(self, ctx):
        guild_id = ctx.guild.id
        if guild_id not in self.config:
            return await ctx.send("Chatfilter isn't enabled")
        if "bots" not in self.config[guild_id]:
            self.config[guild_id]["bots"] = True
            await self.config.flush()
        else:
            await self.config.remove_sub(guild_id, "bots")
        toggle = "Enabled" if "bots" in self.config[guild_id] else "Disabled"
        await ctx.send(f"{toggle} filtering bot messages")

    @commands.Cog.listener()
    async def on_message(self, m: discord.Message):
        if hasattr(m.guild, "id") and m.guild.id in self.config:
            guild_id = m.guild.id
            if not m.author.bot or "bots" in self.config[guild_id]:
                if m.channel.id in self.config[guild_id]["ignored"]:
                    return
                for phrase in self.config[guild_id]["blacklist"]:
                    await asyncio.sleep(0)
                    if "\\" in phrase:
                        m.content = m.content.replace("\\", "")
                    if m.author.bot or not self.bot.attrs.is_moderator(m.author):
                        with suppress(discord.errors.NotFound):
                            for chunk in m.content.split():
                                await asyncio.sleep(0)
                                if phrase in chunk.lower():
                                    await asyncio.sleep(0.5)
                                    await m.delete()
                                    return

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if hasattr(after.guild, "id") and after.guild.id in self.config:
            guild_id = after.guild.id
            if not after.author.bot or "bots" in self.config[guild_id]:
                if after.channel.id in self.config[guild_id]["ignored"]:
                    return
                guild_id = before.guild.id
                if guild_id in self.config and self.config[guild_id]["blacklist"]:
                    for phrase in self.config[guild_id]["blacklist"]:
                        await asyncio.sleep(0)
                        if "\\" not in phrase:
                            after.content = after.content.replace("\\", "")
                        if after.author.bot or not self.bot.attrs.is_moderator(after.author):
                            for chunk in after.content.split():
                                await asyncio.sleep(0)
                                if phrase in chunk.lower():
                                    await asyncio.sleep(0.5)
                                    with suppress(discord.errors.NotFound):
                                        await after.delete()
                                    return


def setup(bot):
    bot.add_cog(ChatFilter(bot))
