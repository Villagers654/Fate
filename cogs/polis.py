import asyncio
import random
from discord.ext import commands
import discord
from utils import checks, colors


class Sliders:

	def max(self):
		e = discord.Embed(color=colors.red())
		e.set_author(name='2B2TMCPE - Minecraft Anarchy', icon_url='https://cdn.discordapp.com/avatars/293420269832503306/a574a59c804e0797da44751e76cf324e.webp?size=1024')
		e.set_thumbnail(url='https://cdn.discordapp.com/icons/630178744908382219/0a254e8cb841ba9a9d3193b5b03da4f8.webp?size=1024')
		e.set_image(url='https://cdn.discordapp.com/icons/630178744908382219/0a254e8cb841ba9a9d3193b5b03da4f8.webp?size=1024')
		e.description = 'This is a minecraft bedrock edition server that is based on 2b2t.org, ' \
		    'and it is complete anarchy. On this server you can do whatever you want: kill players, ' \
		    'spam, trap spawn, hack, fly, poison players, loot, mine. But be aware that other players ' \
		    'will also do the same, and you will die, a lot. Good luck! For more challenges, ' \
		    '(Disclaimer, we have nothing to do with the actual 2b2t.org server). The servers owned by ' \
		    'lordliam8 and Maxxie115 that runs on the server software NukkitX. 2b2tmcpe.org is currently ' \
		    'over 1 year old and has a large and active player base comprised of many Taiwanese and English players.\n' \
		    '**IP:** __2b2tmcpe.org__ **port:** __19132__ **discord: [here](https://discord.gg/dg7j5JF/)**'
		image_urls = [
			'https://cdn.discordapp.com/attachments/630180017921327115/634189147178795019/Screenshot_20190305-215348_BlockLauncher-1.jpg',
			'https://cdn.discordapp.com/attachments/630178745403179040/634189168456630272/IMG_2266.PNG',
			'https://cdn.discordapp.com/attachments/630178745403179040/634189168926392350/IMG_2276.PNG',
			'https://cdn.discordapp.com/attachments/630178745403179040/634189473717944340/IMG_2267.PNG',
			'https://cdn.discordapp.com/attachments/630178745403179040/634195810501787649/image0.jpg'
		]
		e.set_image(url=random.choice(image_urls))
		return e

	def mars(self):
		e = discord.Embed(color=colors.orange())
		e.set_author(name='Mars', icon_url='https://cdn.discordapp.com/avatars/544911653058248734/a_12ff164baa36ae2171358e968d148f4f.gif?size=1024')
		e.set_thumbnail(url='https://cdn.discordapp.com/icons/610638435711189002/a_4841a26e78005fcf7b36974d0ab7d3eb.gif?size=1024')
		e.description = 'Unfinished'
		return e


class Polis(commands.Cog):
	def __init__(self, bot: commands.Bot):
		self.bot = bot
		self.slideshow_interval = 120

	async def showcase_slider(self):
		""" embeded partnership slideshow """
		channel = self.bot.get_channel(610767401386115091)
		msg = await channel.fetch_message(634162917935284226)
		while True:
			servers = [eval(f'Sliders().{func}()') for func in dir(Sliders()) if not func.startswith('__')]
			for embed in servers:
				await msg.edit(embed=embed)
				await asyncio.sleep(self.slideshow_interval)
			await asyncio.sleep(1)

	@commands.command(name='start-slider')
	@commands.check(checks.luck)
	async def start_slider(self, ctx):
		self.bot.loop.create_task(self.showcase_slider())
		await ctx.send('👍', delete_after=3)
		await asyncio.sleep(3)
		await ctx.message.delete()

	@commands.Cog.listener()
	async def on_ready(self):
		self.bot.loop.create_task(self.showcase_slider())

def setup(bot):
	bot.add_cog(Polis(bot))
