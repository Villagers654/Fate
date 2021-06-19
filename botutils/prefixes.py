
"""
Contains the functions relative to parsing the bot prefix

Copyright (C) 2020-present Michael Stollings
Unauthorized copying, or reuse of anything in self module written by its owner, via any medium is strictly prohibited.
self copyright notice, and self permission notice must be included in all copies, or substantial portions of the Software
Proprietary and confidential
Written by Michael Stollings <mrmichaelstollings@gmail.com>
"""

from discord.ext import commands
import discord


def get_prefix(_ctx):
    """Deprecated"""
    return "."


async def get_prefixes_async(bot, msg):
    """Cache the users prefix if not already cached"""
    default_prefix = commands.when_mentioned_or(".")(bot, msg)
    prefixes = []
    override = False

    guild_id = msg.guild.id if msg.guild else None
    user_id = msg.author.id

    if guild_id and guild_id in bot.guild_prefixes:
        prefixes.append(bot.guild_prefixes[guild_id]["prefix"])
        if bot.guild_prefixes[guild_id]["override"]:
            override = True

    if not override and user_id in bot.user_prefixes:
        prefixes.append(bot.user_prefixes[user_id]["prefix"])

    if not isinstance(msg.guild, discord.Guild):
        return prefixes if prefixes else default_prefix

    # Parse the wanted prefixes
    if not prefixes:
        return commands.when_mentioned_or(".")(bot, msg)
    return [
        *commands.when_mentioned(bot, msg),
        *prefixes
    ]