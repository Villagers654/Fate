"""
cogs.utility.notepad
~~~~~~~~~~~~~~~~~~~~~

A cog for jutting down notes for later

:copyright: (C) 2021-present FrequencyX4, All Rights Reserved
:license: Proprietary, see LICENSE for details
"""

from os import path
import json
import os
from io import BytesIO
import requests

from discord.ext import commands
import discord
from PIL import Image, ImageDraw, ImageFont


class NotePad(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.path = "./data/userdata/notepad.json"
        self.font = "./utils/fonts/Modern_Sans_Light.otf"
        self.notes = {}
        if path.isfile(self.path):
            with open(self.path, "r") as f:
                self.notes = json.load(f)

    async def save_data(self):
        async with self.bot.utils.open(self.path, "w+") as f:
            await f.write(await self.bot.utils.dump_json(self.notes))

    @commands.command(name="notepad")
    @commands.cooldown(2, 5, commands.BucketType.user)
    @commands.bot_has_permissions(attach_files=True, embed_links=True)
    async def notepad(self, ctx, your_note=None):
        def add_corners(im, rad):
            """ Adds transparent corners to an img """
            circle = Image.new("L", (rad * 2, rad * 2), 0)
            d = ImageDraw.Draw(circle)
            d.ellipse((0, 0, rad * 2, rad * 2), fill=255)
            alpha = Image.new("L", im.size, 255)
            w, h = im.size
            alpha.paste(circle.crop((0, 0, rad, rad)), (0, 0))
            alpha.paste(circle.crop((0, rad, rad, rad * 2)), (0, h - rad))
            alpha.paste(circle.crop((rad, 0, rad * 2, rad)), (w - rad, 0))
            alpha.paste(circle.crop((rad, rad, rad * 2, rad * 2)), (w - rad, h - rad))
            im.putalpha(alpha)
            return im

        notes = [
            "suicide is not an option, its the answer and test reeeeee owo uwu eee",
            "commit slip n slide cheese grader",
            "erase-o your life-o",
        ]
        yellow = discord.Color(0xE7CA00).to_rgb()
        im = Image.new("RGBA", (1000, 160 + len(notes) * 50), yellow)
        font = ImageFont.truetype("./utils/fonts/Modern_Sans_Light.otf", 40)
        draw = ImageDraw.Draw(im)

        avatar = Image.open(
            BytesIO(requests.get(ctx.author.display_avatar.url).content)
        ).convert("RGBA")
        avatar = add_corners(avatar.resize((175, 175), Image.BICUBIC), 87)
        avatar = avatar.resize((120, 120), Image.BICUBIC)
        im.paste(avatar, (440, 20), avatar)
        draw.ellipse((440, 20, 560, 140), outline="black", width=5)

        pos = 160
        index = 1
        for note in notes:
            for i, text in enumerate(
                [note[i : i + 45] for i in range(0, len(note), 45)]
            ):
                if i == 0:
                    text = f"{index}. {text}"
                else:
                    text = "  " + text
                draw.line((60, pos, 940, pos), fill="black", width=2)
                draw.text((75, pos + 10), text, "black", font)
                pos += 50
            index += 1

        im.save("./static/gay.png")
        await ctx.send(file=discord.File("./static/gay.png"))
        os.remove("./static/gay.png")


def setup(bot):
    bot.add_cog(NotePad(bot), override=True)
