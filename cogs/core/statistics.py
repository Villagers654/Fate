"""
cogs.core.statistics
~~~~~~~~~~~~~~~~~~~~~

A cog for showing the number of servers using each module

:copyright: (C) 2021-present FrequencyX4, All Rights Reserved
:license: Proprietary, see LICENSE for details
"""

from discord.ext import commands
import discord
from botutils import colors


class Statistics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cogs = {  #  CogName: variable
            "Logger": "config",
            "SelfRoles": "config",
            "AutoRole": "config",
            "ChatFilter": "config",
            "AntiSpam": "config",
            "ModMail": "config",
            "Verification": "config",
            "Giveaways": "data",
            "RestoreRoles": "guilds",
            "Welcome": "config",
            "Leave": "toggle",
            "Suggestions": "config"
        }

    @commands.command(name="statistics", aliases=["stats"], description="Shows the number of servers using each module")
    async def statistics(self, ctx):
        e = discord.Embed(color=colors.fate)
        owner = await self.bot.fetch_user(self.bot.config["bot_owner_id"])
        e.set_author(name="Module Statistics", icon_url=owner.display_avatar.url)
        description = {}
        for key, value in self.cogs.items():
            config = getattr(self.bot.cogs[key], value)
            if hasattr(config, "__len__"):
                count = len(config)
            else:
                count = await config.count()
            description[key] = count
        e.description = self.bot.utils.format_dict(description)
        await ctx.send(embed=e)


def setup(bot):
    bot.add_cog(Statistics(bot), override=True)
