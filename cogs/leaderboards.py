from datetime import datetime, timedelta
from discord.ext import commands
from os.path import isfile
import discord
import random
import json
import time

class Leaderboards:
	def __init__(self, bot: commands.Bot):
		self.bot = bot
		self.cd = {}
		self.global_data = {}
		self.guilds_data = {}
		self.monthly_global_data = {}
		self.monthly_guilds_data = {}
		self.gvclb = {}
		self.vclb = {}
		self.dat = {}
		if isfile("./data/userdata/xp.json"):
			with open("./data/userdata/xp.json", "r") as infile:
				dat = json.load(infile)
				if "global" in dat and "guilded" in dat:
					self.global_data = dat["global"]
					self.guilds_data = dat["guilded"]
					self.monthly_global_data = dat["monthly_global"]
					self.monthly_guilds_data = dat["monthly_guilded"]
					self.vclb = dat["vclb"]
					self.gvclb = dat["gvclb"]

	def save_xp(self):
		with open("./data/userdata/xp.json", "w") as outfile:
			json.dump({"global": self.global_data, "guilded": self.guilds_data, "monthly_global": self.monthly_global_data,
			           "monthly_guilded": self.monthly_guilds_data, "vclb": self.vclb, "gvclb": self.gvclb},
			          outfile, sort_keys=True, indent=4, separators=(',', ': '), ensure_ascii=False)

	@commands.command(name="leaderboard", aliases=["lb"])
	@commands.cooldown(1, 10, commands.BucketType.user)
	async def leaderboard(self, ctx):
		embed = discord.Embed(title="Leaderboard", color=0x4A0E50)
		embed.description = ""
		rank = 1
		for user_id, xp in (sorted(self.guilds_data[str(ctx.guild.id)].items(), key=lambda kv: kv[1], reverse=True))[:15]:
			name = "INVALID-USER"
			user = self.bot.get_user(int(user_id))
			if isinstance(user, discord.User):
				name = user.name
			level = str(xp / 750)
			level = level[:level.find(".")]
			embed.description += "‎**‎#{}.** ‎`‎{}`: ‎{} | {}\n".format(rank, name, level, xp)
			rank += 1
			embed.set_thumbnail(url=ctx.guild.icon_url)
			embed.set_footer(text=random.choice(["Powered by CortexPE", "Powered by Luck", "Powered by Tothy", "Powered by Thready", "Powered by slaves", "Powered by Beddys ego", "Powered by Samsung", "Powered by the supreme", "Powered by doritos", "Cooldown: 10 seconds"]))
		await ctx.send(embed=embed)

	@commands.command(name="gleaderboard", aliases=["glb"])
	@commands.cooldown(1, 10, commands.BucketType.user)
	async def gleaderboard(self, ctx):
		embed = discord.Embed(title="Global Leaderboard", color=0x4A0E50)
		embed.description = ""
		rank = 1
		for user_id, xp in (sorted(self.global_data.items(), key=lambda kv: kv[1], reverse=True))[:15]:
			name = "INVALID-USER"
			user = self.bot.get_user(int(user_id))
			if isinstance(user, discord.User):
				name = user.name
			level = str(xp / 750)
			level = level[:level.find(".")]
			embed.description += "‎**#‎{}.** ‎`‎{}`‎ ~ ‎{} | {}\n".format(rank, name, level, xp)
			rank += 1
			embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/501871950260469790/505198377412067328/20181025_215740.png")
			embed.set_footer(text=random.choice(["Powered by CortexPE", "Powered by Luck", "Powered by Tothy", "Powered by Thready", "Powered by slaves", "Powered by Beddys ego", "Powered by Samsung", "Powered by the supreme", "Powered by doritos", "Cooldown: 10 seconds"]))
		await ctx.send(embed=embed)

	@commands.command(name="ggleaderboard", aliases=["gglb"])
	@commands.cooldown(1, 10, commands.BucketType.user)
	async def ggleaderboard(self, ctx):
		embed = discord.Embed(title="Guild XP Leaderboard", color=0x4A0E50)
		embed.description = ""
		rank = 1
		for guild_id, xp in (sorted({i:sum(x.values()) for i, x in self.guilds_data.items()}.items(), key=lambda kv: kv[1], reverse=True))[:8]:
			name = "INVALID-GUILD"
			guild = self.bot.get_guild(int(guild_id))
			if isinstance(guild, discord.Guild):
				name = guild.name
			else:
				del self.guilds_data[guild_id]
			embed.description += "**#{}.** `{}`: {}\n".format(rank, name, xp)
			rank += 1
			embed.set_thumbnail(url=ctx.guild.icon_url)
			embed.set_footer(text=random.choice(["Powered by CortexPE", "Powered by Luck", "Powered by Tothy", "Powered by Thready", "Powered by slaves", "Powered by Beddys ego", "Powered by Samsung", "Powered by the supreme", "Powered by doritos", "Cooldown: 10 seconds"]))
		await ctx.send(embed=embed)

	@commands.command(name="mleaderboard", aliases=["mlb"])
	async def _mleaderboard(self, ctx):
		guild_id = str(ctx.guild.id)
		users = list(self.monthly_guilds_data[guild_id])
		xp = {}
		for user in users:
			for msg in self.monthly_guilds_data[guild_id][user]:
				xp[user] = len(self.monthly_guilds_data[guild_id][user])
		embed = discord.Embed(title="Monthly Leaderboard", color=0x4A0E50)
		embed.description = ""
		rank = 1
		for user_id, xp in (sorted(xp.items(), key=lambda kv: kv[1], reverse=True))[:15]:
			name = "INVALID-USER"
			user = self.bot.get_user(int(user_id))
			if isinstance(user, discord.User):
				name = user.name
			level = str(xp / 750)
			level = level[:level.find(".")]
			embed.description += "‎**#‎{}.** ‎`‎{}`‎ ~ ‎{} | {}\n".format(rank, name, level, xp)
			rank += 1
			embed.set_thumbnail(
				url="https://cdn.discordapp.com/attachments/501871950260469790/505198377412067328/20181025_215740.png")
			embed.set_footer(text=random.choice(
				["Powered by CortexPE", "Powered by Luck", "Powered by Tothy", "Powered by Thready",
				 "Powered by slaves", "Powered by Beddys ego", "Powered by Samsung", "Powered by the supreme",
				 "Powered by doritos", "Cooldown: 10 seconds"]))
		await ctx.send(embed=embed)

	@commands.command(name="gmleaderboard", aliases=["gmlb"])
	async def _gmleaderboard(self, ctx):
		users = list(self.monthly_global_data)
		xp = {}
		for user in users:
			for msg in self.monthly_global_data[user]:
				xp[user] = len(self.monthly_global_data[user])
		embed = discord.Embed(title="Global Monthly Leaderboard", color=0x4A0E50)
		embed.description = ""
		rank = 1
		for user_id, xp in (sorted(xp.items(), key=lambda kv: kv[1], reverse=True))[:15]:
			name = "INVALID-USER"
			user = self.bot.get_user(int(user_id))
			if isinstance(user, discord.User):
				name = user.name
			level = str(xp / 750)
			level = level[:level.find(".")]
			embed.description += "‎**#‎{}.** ‎`‎{}`‎ ~ ‎{} | {}\n".format(rank, name, level, xp)
			rank += 1
			embed.set_thumbnail(
				url="https://cdn.discordapp.com/attachments/501871950260469790/505198377412067328/20181025_215740.png")
			embed.set_footer(text=random.choice(
				["Powered by CortexPE", "Powered by Luck", "Powered by Tothy", "Powered by Thready",
				 "Powered by slaves", "Powered by Beddys ego", "Powered by Samsung", "Powered by the supreme",
				 "Powered by doritos", "Cooldown: 10 seconds"]))
		await ctx.send(embed=embed)

	@commands.command(name="vcleaderboard", aliases=["vclb"])
	@commands.cooldown(1, 10, commands.BucketType.user)
	async def vcleaderboard(self, ctx):
		e = discord.Embed(title="VC Leaderboard", color=0x4A0E50)
		e.description = ""
		rank = 1
		for user_id, xp in (sorted(self.vclb[str(ctx.guild.id)].items(), key=lambda kv: kv[1], reverse=True))[:15]:
			name = "INVALID-USER"
			user = self.bot.get_user(int(user_id))
			if isinstance(user, discord.User):
				name = user.name
			score = timedelta(seconds=xp)
			e.description += "‎**‎#{}.** ‎`‎{}`: ‎{}\n".format(rank, name, score)
			rank += 1
			e.set_thumbnail(url=ctx.guild.icon_url)
			e.set_footer(text=random.choice(["Powered by CortexPE", "Powered by Luck", "Powered by Tothy", "Powered by Thready", "Powered by slaves", "Powered by Beddys ego", "Powered by Samsung", "Powered by the supreme", "Powered by tostitos"]))
		await ctx.send(embed=e)

	@commands.command(name="gvcleaderboard", aliases=["gvclb"])
	@commands.cooldown(1, 10, commands.BucketType.user)
	async def gvcleaderboard(self, ctx):
		embed = discord.Embed(title="Global VC Leaderboard", color=0x4A0E50)
		embed.description = ""
		rank = 1
		for user_id, xp in (sorted(self.gvclb.items(), key=lambda kv: kv[1], reverse=True))[:15]:
			name = "INVALID-USER"
			user = self.bot.get_user(int(user_id))
			if isinstance(user, discord.User):
				name = user.name
			score = timedelta(seconds=xp)
			embed.description += "‎**#‎{}.** ‎`‎{}`‎ ~ ‎{}\n".format(rank, name, score)
			rank += 1
			embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/501871950260469790/505198377412067328/20181025_215740.png")
			embed.set_footer(text=random.choice(["Powered by CortexPE", "Powered by Luck", "Powered by Tothy", "Powered by Thready", "Powered by slaves", "Powered by Beddys ego", "Powered by Samsung", "Powered by the supreme", "Powered by tostitos"]))
		await ctx.send(embed=embed)

	async def on_message(self, m:discord.Message):
		if isinstance(m.guild, discord.Guild):
			if not m.author.bot:
				author_id = str(m.author.id)
				guild_id = str(m.guild.id)
				msg_id = str(m.id)
				if author_id not in self.cd:
					self.cd[author_id] = 0
				if self.cd[author_id] < time.time():
					if guild_id not in self.guilds_data:
						self.guilds_data[guild_id] = {}
					if author_id not in self.guilds_data[guild_id]:
						self.guilds_data[guild_id][author_id] = 0
					if author_id not in self.global_data:
						self.global_data[author_id] = 0
					if author_id not in self.monthly_global_data:
						self.monthly_global_data[author_id] = {}
					if guild_id not in self.monthly_guilds_data:
						self.monthly_guilds_data[guild_id] = {}
					if author_id not in self.monthly_guilds_data[guild_id]:
						self.monthly_guilds_data[guild_id][author_id] = {}

					self.global_data[author_id] += 1
					self.guilds_data[guild_id][author_id] += 1
					self.monthly_global_data[author_id][msg_id] = time.time()
					self.monthly_guilds_data[guild_id][author_id][msg_id] = time.time()
					self.cd[author_id] = time.time() + 10

					for msg_id, msg_time in (sorted(self.monthly_global_data[author_id].items(), key=lambda kv: kv[1], reverse=True)):
						if float(msg_time) < time.time() - 2592000:
							del self.monthly_global_data[author_id][str(msg_id)]

					for msg_id, msg_time in (sorted(self.monthly_guilds_data[guild_id][author_id].items(), key=lambda kv: kv[1], reverse=True)):
						if float(msg_time) < time.time() - 2592000:
							del self.monthly_guilds_data[guild_id][author_id][str(msg_id)]
					self.save_xp()

	async def on_voice_state_update(self, member, before, after):
		if isinstance(member.guild, discord.Guild):
			if not member.bot:
				guild_id = str(member.guild.id)
				user_id = str(member.id)
				if guild_id not in self.vclb:
					self.vclb[guild_id] = {}
				if user_id not in self.vclb[guild_id]:
					self.vclb[guild_id][user_id] = 0
				if user_id not in self.gvclb:
					self.gvclb[user_id] = 0
				if not before.channel:
					self.dat[user_id] = datetime.now()
				if before.afk is True and after.afk is False:
					self.dat[user_id] = datetime.now()
				if not after.channel:
					if user_id in self.dat:
						seconds = (datetime.now() - self.dat[user_id]).seconds
						self.vclb[guild_id][user_id] += seconds
						self.gvclb[user_id] += seconds
						del self.dat[user_id]
				if after.afk:
					if user_id in self.dat:
						seconds = (datetime.now() - self.dat[user_id]).seconds
						self.vclb[guild_id][user_id] += seconds
						self.gvclb[user_id] += seconds
						del self.dat[user_id]
				self.save_xp()

	async def on_guild_remove(self, guild):
		guild_id = str(guild.id)
		if guild_id in self.guilds_data:
			del self.guilds_data[guild_id]

def setup(bot: commands.Bot):
	bot.add_cog(Leaderboards(bot))
