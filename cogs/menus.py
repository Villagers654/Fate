from utils import bytes2human as p, menus as m
from discord.ext import commands
import discord
import asyncio
import random
import psutil
import time
import os

class Menus:
	def __init__(self, bot):
		self.bot = bot

	@commands.group(name='help')
	@commands.cooldown(1, 5, commands.BucketType.user)
	async def _help(self, ctx):
		if ctx.invoked_subcommand is None:
			e = discord.Embed(title="~~~====🥂🍸🍷Help🍷🍸🥂====~~~", color=0x80b0ff)
			e.add_field(name="◈ Core ◈", value="`leaderboard` `gleaderboard` `ggleaderboard` `mleaderboard` `gmleaderboard` `partners` `discords` `servers` `realms` `repeat` `links` `ping` `info`", inline=False)
			e.add_field(name="◈ Responses ◈", value="**`disableresponses` `enableresponses`:** `@Fate` `hello` `ree` `kys` `gm` `gn`", inline=False)
			e.add_field(name="◈ Music ◈", value="`join` `summon` `play` `stop` `skip` `pause` `resume` `volume` `queue` `remove` `shuffle` `dc` `np`", inline=False)
			e.add_field(name="◈ Utility ◈", value="`channelinfo` `servericon` `serverinfo` `userinfo` `autorole` `addemoji` `fromemoji` `delemoji` `makepoll` `welcome` `farewell` `logger` `owner` `avatar` `topic` `timer` `limit` `lock` `lockb` `lockm` `note` `quicknote` `notes` `wiki` `find` `ud` `id`", inline=False)
			e.add_field(name="◈ Reactions ◈", value="`intimidate` `powerup` `observe` `disgust` `admire` `angery` `cuddle` `teasip` `psycho` `thonk` `shrug` `yawn` `hide` `wine` `sigh` `kiss` `kill` `slap` `hug` `pat` `cry`", inline=False)
			e.add_field(name="◈ Mod ◈", value="`mute` `unmute` `vcmute` `vcunmute` `warn` `clearwarns` `addrole` `removerole` `selfroles` `delete` `purge` `nick` `massnick` `kick` `mute` `ban` `pin`", inline=False)
			e.add_field(name="◈ Fun ◈", value="`personality` `liedetector` `fancify` `coffee` `encode` `decode` `choose` `notice` `quote` `mock` `meme` `rate` `roll` `soul` `gay` `sue` `fap` `ask` `rps` `rr` `cookie` `shoot` `inject` `slice` `boop` `stab` `kill`", inline=False)
			try:
				await ctx.author.send(embed=e)
				await ctx.send("Help menu sent to your dm ✅")
			except:
				await ctx.send("Failed to send help menu to dm ❎", embed=e)
				def pred(m):
					return m.channel.id == ctx.channel.id and m.author.id == ctx.author.id
				try:
					msg = await self.bot.wait_for('message', check=pred, timeout=25)
				except asyncio.TimeoutError:
					pass
				else:
					if msg.content.lower() == "k":
						await ctx.message.delete()
						await asyncio.sleep(0.5)
						await msg.delete()
						async for msg in ctx.channel.history(limit=10):
							if msg.author.id == self.bot.user.id:
								if len(msg.embeds) > 0:
									await msg.delete()
									break

	@commands.command(name='info')
	@commands.cooldown(1, 5, commands.BucketType.user)
	async def info(self, ctx):
		m, s = divmod(time.time() - self.bot.START_TIME, 60)
		h, m = divmod(m, 60)
		guilds = len(list(self.bot.guilds))
		users = len(list(self.bot.users))
		fate = self.bot.get_user(506735111543193601)
		luck = self.bot.get_user(264838866480005122)
		path = os.getcwd() + "/data/images/banners/" + random.choice(os.listdir(os.getcwd() + "/data/images/banners/"))
		f = psutil.Process(os.getpid())
		e=discord.Embed(color=0x80b0ff)
		e.set_author(name="Fate [Zerø]: Core Info", icon_url=luck.avatar_url)
		e.description = f'https://discord.gg/BQ23Z2E'
		e.set_thumbnail(url=fate.avatar_url)
		e.set_image(url="attachment://" + os.path.basename(path))
		e.add_field(name="◈ Summary ◈", value="Fate is a ~~multipurpose~~ hybrid bot created for ~~sexual assault~~ fun", inline=False)
		e.add_field(name="◈ Credits ◈", value="• Tothy ~ `rival`\n• Cortex ~ `teacher`", inline=False)
		e.add_field(name="◈ Statistics ◈", value=f'Commands: [{len(self.bot.commands)}]\nServers: [{guilds}]\nUsers: [{users}]', inline=False)
		e.add_field(name="◈ Memory ◈", value=
		f"__**Storage**__: [{p.bytes2human(psutil.disk_usage('/').used)}/{p.bytes2human(psutil.disk_usage('/').total)}]\n"
		f"__**RAM**__: **Global**: {p.bytes2human(psutil.virtual_memory().used)} **Bot**: {p.bytes2human(f.memory_full_info().rss)}\n"
		f"__**CPU**__: **Global**: {psutil.cpu_percent(interval=1)}% **Bot**: {f.cpu_percent(interval=1)}%\n")
		e.set_footer(text="Uptime: {} Hours {} Minutes {} seconds".format(int(h), int(m), int(s)))
		await ctx.send(file=discord.File(path, filename=os.path.basename(path)), embed=e)
		def pred(m):
			return m.channel.id == ctx.channel.id and m.author.id == ctx.author.id
		try:
			msg = await self.bot.wait_for('message', check=pred, timeout=25)
		except asyncio.TimeoutError:
			pass
		else:
			if msg.content.lower() == "k":
				await ctx.message.delete()
				await asyncio.sleep(0.5)
				await msg.delete()
				async for msg in ctx.channel.history(limit=10):
					if msg.author.id == self.bot.user.id:
						if len(msg.embeds) > 0:
							await msg.delete()
							break

# ~== Ads ==~

	@commands.command()
	@commands.cooldown(1, 5, commands.BucketType.user)
	async def discords(self, ctx):
		e=discord.Embed(title="~~~====🥂🍸🍷Discords🍷🍸🥂====~~~", color=0x80b0ff)
		e.add_field(name="• Anarchy Community", value="[Bridge of Anarchism](https://discord.gg/WN9F82d)\n[2p2e - 2pocket2edition](https://discord.gg/y4V4T84)\n[4B4T (Official)](https://discord.gg/BQ23Z2E)\n[4b4t §pawn Patrol](https://discord.gg/5hn4K8E)", inline=False)
		e.add_field(name="• Games", value="[PUBG Mobile](https://discord.gg/gVe27r4)", inline=False)
		e.add_field(name="• Misc", value="[Memes (Tothers Hotel)](https://discord.gg/TzGNyRg)\n[Threadys Alpha server](https://discord.gg/6tcqMUt)", inline=False)
		await ctx.send(embed=e)
		def pred(m):
			return m.channel.id == ctx.channel.id and m.author.id == ctx.author.id
		try:
			msg = await self.bot.wait_for('message', check=pred, timeout=25)
		except asyncio.TimeoutError:
			pass
		else:
			if msg.content.lower() == "k":
				await ctx.message.delete()
				await asyncio.sleep(0.5)
				await msg.delete()
				async for msg in ctx.channel.history(limit=10):
					if msg.author.id == self.bot.user.id:
						if len(msg.embeds) > 0:
							await msg.delete()
							break

	@commands.command()
	@commands.cooldown(1, 5, commands.BucketType.user)
	async def servers(self, ctx):
		e=discord.Embed(title="~~~====🥂🍸🍷Servers🍷🍸🥂====~~~", color=0x80b0ff)
		e.add_field(name="• Anarchy", value="• 4b4t.net : 19132", inline=False)
		await ctx.send(embed=e)
		def pred(m):
			return m.channel.id == ctx.channel.id and m.author.id == ctx.author.id
		try:
			msg = await self.bot.wait_for('message', check=pred, timeout=25)
		except asyncio.TimeoutError:
			pass
		else:
			if msg.content.lower() == "k":
				await ctx.message.delete()
				await asyncio.sleep(0.5)
				await msg.delete()
				async for msg in ctx.channel.history(limit=10):
					if msg.author.id == self.bot.user.id:
						if len(msg.embeds) > 0:
							await msg.delete()
							break

	@commands.command()
	@commands.cooldown(1, 5, commands.BucketType.user)
	async def realms(self, ctx):
		embed=discord.Embed(title="~~~====🥂🍸🍷Realms🍷🍸🥂====~~~", color=0x80b0ff)
		embed.add_field(name="• Anarchy Realms", value="Jappie Anarchy\n• https://realms.gg/pmElWWx5xMk\nAnarchy Realm\n• https://realms.gg/GyxzF5xWnPc\n2c2b Anarchy\n• https://realms.gg/TwbBfe0jGDc\nFraughtian Anarchy\n• https://realms.gg/rdK57KvnA8o\nChaotic Realm\n• https://realms.gg/nzDX1drovu4", inline=False)
		embed.add_field(name="• Misc", value=".", inline=False)
		await ctx.send(embed=embed)
		def pred(m):
			return m.channel.id == ctx.channel.id and m.author.id == ctx.author.id
		try:
			msg = await self.bot.wait_for('message', check=pred, timeout=25)
		except asyncio.TimeoutError:
			pass
		else:
			if msg.content.lower() == "k":
				await ctx.message.delete()
				await asyncio.sleep(0.5)
				await msg.delete()
				async for msg in ctx.channel.history(limit=10):
					if msg.author.id == self.bot.user.id:
						if len(msg.embeds) > 0:
							await msg.delete()
							break

# ~== 4B4T ==~

	async def on_message(self, message: discord.Message):
		if not message.author.bot:
			if message.content.startswith(".4b4t"):
				guild = self.bot.get_guild(470961230362837002)
				e=discord.Embed(title=guild.name, color=0x0000ff)
				e.set_thumbnail(url=guild.icon_url)
				e.add_field(name="◈ Main Info ◈", value="• be sure to mention a mod\nhouse keeper or higher to\nget the player role if you\nplay on the mc server", inline=False)
				e.add_field(name="◈ Server Info ◈", value="**ip:** 4b4t.net : 19132\n**Version:** 1.7.0", inline=False)
				e.add_field(name="◈ Commands ◈", value="• submitmotd ~ `submits a MOTD`\n• reportbug ~ `report a bug`\n• rules ~ `4b4t's discord rules`\n• vote ~ `vote for 4b4t`", inline=False)
				await message.channel.send(embed=e)

# ~== Misc ==~

	@commands.command()
	async def partners(self, ctx):
		luck = self.bot.get_user(264838866480005122)
		bottest = self.bot.get_guild(501868216147247104)
		fourbfourt = "https://discord.gg/BQ23Z2E"
		totherbot = "https://discordapp.com/api/oauth2/authorize?client_id=452289354296197120&permissions=0&scope=bot"
		spookiehotel = "https://discord.gg/DVcF6Yn"
		threadysserver = "https://discord.gg/6tcqMUt"
		e=discord.Embed(color=0xffffff)
		e.set_author(name=f'🥃🥂🍸🍷Partners🍷🍸🥂🥃', icon_url=luck.avatar_url)
		e.description = "Wanna partner? dm Luck#1574"
		e.set_thumbnail(url=bottest.icon_url)
		e.add_field(name="◈ Servers ◈", value=f'• [Threadys Server]({threadysserver})\n• [Spookie Hotel]({spookiehotel})\n• [4b4t]({fourbfourt})', inline=False)
		e.add_field(name="◈ Bots ◈", value=f'• [TotherBot]({totherbot})', inline=False)
		await ctx.send(embed=e)
		def pred(m):
			return m.channel.id == ctx.channel.id and m.author.id == ctx.author.id
		try:
			msg = await self.bot.wait_for('message', check=pred, timeout=25)
		except asyncio.TimeoutError:
			pass
		else:
			if msg.content.lower() == "k":
				await ctx.message.delete()
				await asyncio.sleep(0.5)
				await msg.delete()
				async for msg in ctx.channel.history(limit=10):
					if msg.author.id == self.bot.user.id:
						if len(msg.embeds) > 0:
							await msg.delete()
							break

	@commands.command()
	@commands.cooldown(1, 5, commands.BucketType.user)
	async def credits(self, ctx, content='repeating'):
		embed=discord.Embed(title="~~~====🥂🍸🍷Credits🍷🍸🥂====~~~", color=0x80b0ff)
		embed.add_field(name="CortexPE#8680", value="• Tought me litterally 99.9% of fates code (and dealt with my storms of questions)", inline=False)
		embed.add_field(name="Tothy", value="• existed", inline=False)
		await ctx.send(embed=embed)
		def pred(m):
			return m.channel.id == ctx.channel.id and m.author.id == ctx.author.id
		try:
			msg = await self.bot.wait_for('message', check=pred, timeout=25)
		except asyncio.TimeoutError:
			pass
		else:
			if msg.content.lower() == "k":
				await ctx.message.delete()
				await asyncio.sleep(0.5)
				await msg.delete()
				async for msg in ctx.channel.history(limit=10):
					if msg.author.id == self.bot.user.id:
						if len(msg.embeds) > 0:
							await msg.delete()
							break

def setup(bot):
	bot.add_cog(Menus(bot))
