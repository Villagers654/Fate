# Customizable xp ranking system

from os import path
import os
import json
from time import time, monotonic
from random import *
import asyncio
from datetime import datetime, timedelta

from discord.ext import commands
import discord

from utils import colors


class Ranking(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.path = './static/xp.json'
		self.globals = [
			'msg', 'monthly_msg', 'vc'
		]

		if not path.exists('xp'):
			os.mkdir('xp')
			os.mkdir(path.join('xp', 'global'))
			os.mkdir(path.join('xp', 'guilds'))
			for filename in self.globals:
				with open(path.join('xp', 'global', filename) + '.json', 'w') as f:
					json.dump({}, f, ensure_ascii=False)

		self.msg = self._global('msg')
		self.monthly_msg = self._global('monthly_msg')
		self.gvclb = self._global('vc')

		self.guilds = {}
		for directory in os.listdir(path.join('xp', 'guilds')):
			if directory.isdigit():
				self.guilds[directory] = {}
				for filename in os.listdir(path.join('xp', 'guilds', directory)):
					if '.json' in filename:
						try:
							with open(path.join('xp', 'guilds', directory, filename), 'r') as f:
								self.guilds[directory][filename.replace('.json', '')] = json.load(f)
						except json.JSONDecodeError:
							with open(path.join('xp', 'guilds', directory, 'backup', filename), 'r') as f:
								self.guilds[directory][filename.replace('.json', '')] = json.load(f)

		self.msg_cooldown = 10
		self.cd = {}
		self.global_cd = {}
		self.macro_cd = {}
		self.counter = 0
		self.vc_counter = 0
		self.backup_counter = 0
		self.cache = {}
		self.config = {}
		if path.isfile(self.path):
			with open(self.path, 'r') as f:
				self.config = json.load(f)

	def _global(self, Global) -> dict:
		""" Returns data for each global leaderboard """
		try:
			with open(path.join('xp', 'global', Global) + '.json', 'r') as f:
				return json.load(f)
		except json.JSONDecodeError:
			with open(path.join('xp', 'global', 'backup', Global + '.json'), 'r') as f:
				return json.load(f)

	def save_config(self):
		""" Saves per-server configuration """
		with open(self.path, 'w') as f:
			json.dump(self.config, f)

	def static_config(self):
		""" Default config """
		return {
			"min_xp_per_msg": 1,
			"max_xp_per_msg": 1,
			"base_level_xp_req": 100,
			"timeframe": 10,
			"msgs_within_timeframe": 1
		}

	def init(self, guild_id: str):
		""" Saves static config as the guilds initial config """
		self.config[guild_id] = self.static_config()
		self.save_config()

	def calc_lvl(self, total_xp):
		def x(level):
			x = 1; y = 0.125; lmt = 3
			for i in range(level):
				if x >= lmt:
					y = y / 2
					lmt += 3
				x += y
			return x

		level = 0; levels = [[0, 250]]
		lvl_up = 1; sub = 0; progress = 0
		for xp in range(total_xp):
			requirement = 0
			for lvl, xp_req in levels:
				requirement += xp_req
			if xp > requirement:
				level += 1
				levels.append([level, 250 * x(level)])
				lvl_up = 250 * x(level)
				sub = requirement
			progress = xp - sub

		return {
			'level': round(level),
			'level_up': round(lvl_up),
			'xp': round(progress)
		}

	@commands.Cog.listener()
	async def on_message(self, msg):
		if msg.guild and not msg.author.bot:
			guild_id = str(msg.guild.id)
			user_id = str(msg.author.id)
			guild_path = path.join('xp', 'guilds', guild_id)

			conf = self.static_config()  # type: dict
			if guild_id in self.config:
				conf = self.config[guild_id]
			xp = randint(conf['min_xp_per_msg'], conf['max_xp_per_msg'])

			# global leveling
			if user_id not in self.global_cd:
				self.global_cd[user_id] = 0
			if self.global_cd[user_id] < time() - 10:
				if user_id not in self.msg:
					self.msg[user_id] = 0
				if user_id not in self.monthly_msg:
					self.monthly_msg[user_id] = {}

				self.msg[user_id] += xp
				self.monthly_msg[user_id][str(time())] = xp

				self.counter += 1
				if self.counter >= 10:
					with open(path.join('xp', 'global', 'msg.json'), 'w') as f:
						json.dump(self.msg, f, ensure_ascii=False)
					with open(path.join('xp', 'global', 'monthly_msg.json'), 'w') as f:
						json.dump(self.monthly_msg, f, ensure_ascii=True)
					self.counter = 0

			# per-server leveling
			if guild_id not in self.cd:
				self.cd[guild_id] = {}
			if user_id not in self.cd[guild_id]:
				self.cd[guild_id][user_id] = []
			msgs = [x for x in self.cd[guild_id][user_id] if x > time() - conf['timeframe']]
			if len(msgs) < conf['msgs_within_timeframe']:
				self.cd[guild_id][user_id].append(time())
				if not path.isdir(guild_path):
					os.mkdir(guild_path)
					for filename in self.globals:
						with open(path.join(guild_path, filename) + '.json', 'w') as f:
							json.dump({}, f, ensure_ascii=False)
					self.guilds[guild_id] = {
						Global: {} for Global in self.globals
					}
				if user_id not in self.guilds[guild_id]['msg']:
					self.guilds[guild_id]['msg'][user_id] = 0
				if user_id not in self.guilds[guild_id]['monthly_msg']:
					self.guilds[guild_id]['monthly_msg'][user_id] = {}

				self.guilds[guild_id]['msg'][user_id] += xp
				self.guilds[guild_id]['monthly_msg'][user_id][str(time())] = xp

				with open(path.join(guild_path, 'msg.json'), 'w') as f:
					json.dump(self.guilds[guild_id]['msg'], f, ensure_ascii=False)
				with open(path.join(guild_path, 'monthly_msg.json'), 'w') as f:
					json.dump(self.guilds[guild_id]['monthly_msg'], f, ensure_ascii=False)

				self.backup_counter += 1
				if self.backup_counter > 25:
					# per-guild backup
					if not path.exists(path.join(guild_path, 'backup')):
						os.mkdir(path.join(guild_path, 'backup'))
					for filename in os.listdir(guild_path):
						if '.' in filename:
							with open(path.join(guild_path, filename), 'r') as rf:
								with open(path.join(guild_path, 'backup', filename), 'w') as wf:
									wf.write(rf.read())
					# global backup
					backup_path = path.join('xp', 'global', 'backup')
					if not path.exists(backup_path):
						os.mkdir(backup_path)
					for filename in os.listdir(path.join('xp', 'global')):
						if '.' in filename:
							with open(path.join('xp', 'global', filename), 'r') as rf:
								with open(path.join(backup_path, filename), 'w') as wf:
									wf.write(rf.read())
					self.backup_counter = 0

	@commands.Cog.listener()
	async def on_voice_state_update(self, user, before, after):
		if isinstance(user.guild, discord.Guild):
			guild_id = str(user.guild.id)
			channel_id = None  # type: discord.TextChannel
			if before.channel:
				channel_id = str(before.channel.id)
			if after.channel:
				channel_id = str(after.channel.id)
			user_id = str(user.id)
			guild_path = path.join('xp', 'guilds', guild_id)
			if guild_id not in self.guilds:
				self.guilds[guild_id] = {
					Global: {} for Global in self.globals
				}
				os.mkdir(guild_path)
				for filename in self.globals:
					with open(path.join(guild_path, filename + '.json'), 'w') as f:
						json.dump({}, f)
			if user_id not in self.guilds[guild_id]['vc']:
				self.guilds[guild_id]['vc'][user_id] = 0
			if user_id not in self.gvclb:
				self.gvclb[user_id] = 0
			if channel_id not in self.cache:
				self.cache[channel_id] = {}
				self.cache[channel_id]['members'] = {}
			def get_active_members(channel):
				members = []
				total = 0
				for member in channel.members:
					if not member.bot:
						total += 1
						state = member.voice
						if not state.mute and not state.self_mute:
							if not state.deaf and not state.self_deaf:
								members.append(member)
				return (members, total)
			async def wrap(channel):
				cid = str(channel.id)
				for member_id in list(self.cache[cid]['members'].keys()):
					seconds = (datetime.now() - self.cache[cid]['members'][member_id]).seconds
					self.guilds[guild_id]['vc'][member_id] += seconds
					self.gvclb[member_id] += seconds
					del self.cache[cid]['members'][member_id]
					save()
			async def run(channel):
				channel_id = str(channel.id)
				members, total = get_active_members(channel)
				if len(members) == 0 or len(members) == 1 and len(members) == total:
					return await wrap(channel)
				for member in channel.members:
					if member not in self.cache[channel_id]['members']:
						if not member.bot:
							member_id = str(member.id)
							if member_id not in self.cache[channel_id]['members']:
								self.cache[channel_id]['members'][member_id] = datetime.now()
			def save():
				with open(path.join('xp', 'guilds', guild_id, 'vc.json'), 'w') as f:
					json.dump(self.guilds[guild_id]['vc'], f)
				with open(path.join('xp', 'global', 'vc.json'), 'w') as f:
					json.dump(self.gvclb, f)
				self.vc_counter = 0
			if before.channel and after.channel:
				if before.channel.id != after.channel.id:
					channel_id = str(before.channel.id)
					if user_id in self.cache[channel_id]['members']:
						seconds = (datetime.now() - self.cache[channel_id]['members'][user_id]).seconds
						self.guilds[guild_id]['vc'][user_id] += seconds
						self.gvclb[user_id] += seconds
						del self.cache[channel_id]['members'][user_id]
						save()
					await run(before.channel)
					await run(after.channel)
			if not after.channel:
				channel_id = str(before.channel.id)
				if user_id in self.cache[channel_id]['members']:
					seconds = (datetime.now() - self.cache[channel_id]['members'][user_id]).seconds
					self.guilds[guild_id]['vc'][user_id] += seconds
					self.gvclb[user_id] += seconds
					del self.cache[channel_id]['members'][user_id]
					save()
					await run(before.channel)
			if before.channel is not None:
				await run(before.channel)
			if after.channel is not None:
				await run(after.channel)

	@commands.command(
		name='leaderboard',
		aliases=[
			'lb', 'mlb', 'vclb', 'glb', 'gmlb', 'gvclb', 'gglb', 'ggvclb',
			'mleaderboard', 'vcleaderboard', 'gleaderboard', 'gvcleaderboard',
			'ggleaderboard', 'ggvcleaderboard'
		]
	)
	@commands.cooldown(1, 60, commands.BucketType.user)
	@commands.cooldown(1, 3, commands.BucketType.channel)
	@commands.bot_has_permissions(embed_links=True, manage_messages=True, add_reactions=True)
	async def leaderboard(self, ctx):
		guild_id = str(ctx.guild.id)
		default = discord.Embed()
		default.description = 'Collecting Leaderboard Data..'

		async def wait_for_reaction() -> list:
			def check(reaction, user):
				return user == ctx.author

			try:
				reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
			except asyncio.TimeoutError:
				return [None, None]
			else:
				return [reaction, str(reaction.emoji)]

		def lb():
			e = discord.Embed(color=0x4A0E50)
			e.title = "Leaderboard"
			e.description = ""
			rank = 1
			for user_id, xp in (sorted(self.guilds[guild_id]['msg'].items(), key=lambda kv: kv[1], reverse=True))[:15]:
				name = "INVALID-USER"
				user = self.bot.get_user(int(user_id))
				if isinstance(user, discord.User):
					name = user.name
				level = self.calc_lvl(xp)['level']
				e.description += f'**#{rank}.** `{name}`: {level} | {xp}\n'
				rank += 1
			if ctx.guild.icon_url:
				e.set_thumbnail(url=ctx.guild.icon_url)
			else:
				e.set_thumbnail(url=self.bot.user.avatar_url)
			return e

		def glb():
			e = discord.Embed(color=0x4A0E50)
			e.title = 'Global Leaderboard'
			e.description = ''
			rank = 1
			for user_id, xp in (sorted(self.msg.items(), key=lambda kv: kv[1], reverse=True))[:15]:
				name = 'INVALID-USER'
				user = self.bot.get_user(int(user_id))
				if isinstance(user, discord.User):
					name = user.name
				level = self.calc_lvl(xp)['level']
				e.description += f'**#{rank}.** `{name}`: {level} | {xp}\n'
				rank += 1
			e.set_thumbnail(
				url='https://cdn.discordapp.com/attachments/501871950260469790/505198377412067328/20181025_215740.png')
			return e

		def mlb():
			xp = {}
			for user in list(self.guilds[guild_id]['monthly_msg']):
				xp[user] = len(self.guilds[guild_id]['monthly_msg'][user])
			e = discord.Embed(title="Monthly Leaderboard", color=0x4A0E50)
			e.description = ""
			rank = 1
			for user_id, xp in (sorted(xp.items(), key=lambda kv: kv[1], reverse=True))[:15]:
				name = "INVALID-USER"
				user = self.bot.get_user(int(user_id))
				if isinstance(user, discord.User):
					name = user.name
				level = self.calc_lvl(xp)['level']
				e.description += f'**#{rank}.** `{name}`: {level} | {xp}\n'
				rank += 1
			if ctx.guild.icon_url:
				e.set_thumbnail(url=ctx.guild.icon_url)
			else:
				e.set_thumbnail(url=self.bot.user.avatar_url)
			return e

		def gmlb():
			xp = {}
			for user in list(self.monthly_msg):
				xp[user] = len(self.monthly_msg[user])
			e = discord.Embed(color=0x4A0E50)
			e.title = 'Global Monthly Leaderboard'
			e.description = ""
			rank = 1
			for user_id, xp in (sorted(xp.items(), key=lambda kv: kv[1], reverse=True))[:15]:
				name = 'INVALID-USER'
				user = self.bot.get_user(int(user_id))
				if isinstance(user, discord.User):
					name = user.name
				level = self.calc_lvl(xp)['level']
				e.description += f'**#{rank}.** `{name}`: {level} | {xp}\n'
				rank += 1
			e.set_thumbnail(
				url='https://cdn.discordapp.com/attachments/501871950260469790/505198377412067328/20181025_215740.png')
			return e

		def gglb():
			e = discord.Embed(color=0x4A0E50)
			e.title = 'Guild Leaderboard'
			e.description = ""
			rank = 1
			for guild_id, xp in (sorted({i: sum(x['msg'].values()) for i, x in self.guilds.items()}.items(), key=lambda kv: kv[1], reverse=True))[:8]:
				guild = self.bot.get_guild(int(guild_id))
				if not isinstance(guild, discord.Guild):
					continue
				name = str(guild)
				e.description += f'**#{rank}.** `{name}`: {xp}\n'
				rank += 1
			if ctx.guild.icon_url:
				e.set_thumbnail(url=ctx.guild.icon_url)
			else:
				e.set_thumbnail(url=self.bot.user.avatar_url)
			return e

		def vclb():
			e = discord.Embed(color=0x4A0E50)
			e.title = 'VC Leaderboard'
			e.description = ""
			rank = 1
			for user_id, xp in (sorted(self.guilds[str(ctx.guild.id)]['vc'].items(), key=lambda kv: kv[1], reverse=True))[:15]:
				name = "INVALID-USER"
				user = self.bot.get_user(int(user_id))
				if isinstance(user, discord.User):
					name = user.name
				score = timedelta(seconds=xp)
				e.description += f'‎**‎#{rank}.** ‎`‎{name}`: ‎{score}\n'
				rank += 1
			if ctx.guild.icon_url:
				e.set_thumbnail(url=ctx.guild.icon_url)
			else:
				e.set_thumbnail(url=self.bot.user.avatar_url)
			return e

		def gvclb():
			e = discord.Embed(color=0x4A0E50)
			e.title = 'Global VC Leaderboard'
			e.description = ""
			rank = 1
			for user_id, xp in (sorted(self.gvclb.items(), key=lambda kv: kv[1], reverse=True))[:15]:
				name = "INVALID-USER"
				user = self.bot.get_user(int(user_id))
				if isinstance(user, discord.User):
					name = user.name
				score = timedelta(seconds=xp)
				e.description += f'‎**‎#{rank}.** ‎`‎{name}`: ‎{score}\n'
				rank += 1
			e.set_thumbnail(url="https://cdn.discordapp.com/attachments/501871950260469790/505198377412067328/20181025_215740.png")
			return e

		def ggvclb():
			e = discord.Embed(color=0x4A0E50)
			e.title = 'Guilded VC Leaderboard'
			e.description = ""
			dat = {}
			for guild_id in self.guilds.keys():
				dat[guild_id] = 0
				for xp in self.guilds[guild_id]['vc'].values():
					dat[guild_id] += xp
			rank = 1
			index = 1
			for guild_id, xp in (sorted(dat.items(), key=lambda kv: kv[1], reverse=True)):
				guild = self.bot.get_guild(int(guild_id))
				if isinstance(guild, discord.Guild):
					name = guild.name
				else:
					continue
				score = timedelta(seconds=xp)
				e.description += f'‎**‎#{rank}.** ‎`‎{name}`: ‎{score}\n'
				rank += 1
				if index == 15:
					break
				index += 1
			e.set_thumbnail(
				url="https://cdn.discordapp.com/attachments/501871950260469790/505198377412067328/20181025_215740.png")
			return e

		with open('./data/config.json', 'r') as f:
			config = json.load(f)  # type: dict
		prefix = '.'  # default prefix
		if guild_id in config['prefix']:
			prefix = config['prefix'][guild_id]
		target = ctx.message.content.split()[0]
		aliases = [
			('lb', 'leaderboard'),
			('mlb', 'mleaderboard'),
			('vclb', 'vcleaderboard'),
			('glb', 'gleaderboard'),
			('gmlb', 'gmleaderboard'),
			('gvclb', 'gvcleaderboard'),
			('gglb', 'ggleaderboard'),
			('ggvclb', 'ggvcleaderboard')
		]
		for cmd, alias in aliases:
			if target == alias:
				target = cmd
		cut_length = len(target) - len(prefix)
		embed = eval(f'{target[-cut_length:]}()')
		msg = await ctx.send(embed=embed)
		await msg.add_reaction('🚀')
		reaction, emoji = await wait_for_reaction()
		await msg.clear_reactions()
		if not reaction:
			return
		if emoji != '🚀':
			return
		await msg.edit(embed=default)
		emojis = ['🏡', '⏮', '⏪', '⏩', '⏭']
		index = 0; sub_index = None
		embeds = [lb(), vclb(), glb(), gvclb(), mlb(), gmlb(), gglb(), ggvclb()]
		await msg.edit(embed=embeds[0])

		def index_check(index):
			if index > len(embeds) - 1:
				index = len(embeds) - 1
			if index < 0:
				index = 0
			return index

		for emoji in emojis:
			await msg.add_reaction(emoji)
			await asyncio.sleep(0.5)
		while True:
			reaction, emoji = await wait_for_reaction()
			if not reaction:
				return await msg.clear_reactions()
			if emoji == emojis[0]:  # home
				index = 0; sub_index = None
			if emoji == emojis[1]:
				index -= 2; sub_index = None
				if isinstance(embeds[index], list):
					sub_index = 0
			if emoji == emojis[2]:
				if isinstance(embeds[index], list):
					if not isinstance(sub_index, int):
						sub_index = len(embeds[index]) - 1
					else:
						if sub_index == 0:
							index -= 1; sub_index = None
							index = index_check(index)
							if isinstance(embeds[index], list):
								sub_index = len(embeds[index]) - 1
						else:
							sub_index -= 1
				else:
					index -= 1
					if isinstance(embeds[index], list):
						sub_index = len(embeds[index]) - 1
			if emoji == emojis[3]:
				if isinstance(embeds[index], list):
					if not isinstance(sub_index, int):
						sub_index = 0
					else:
						if sub_index == len(embeds[index]) - 1:
							index += 1; sub_index = None
							index = index_check(index)
							if isinstance(embeds[index], list):
								sub_index = 0
						else:
							sub_index += 1
				else:
					index += 1
					index = index_check(index)
					if isinstance(embeds[index], list):
						sub_index = 0
			if emoji == emojis[4]:
				index += 2; sub_index = None
				index = index_check(index)
				if isinstance(embeds[index], list):
					sub_index = 0
			if index > len(embeds) - 1:
				index = len(embeds) - 1
			if index < 0:
				index = 0
			if isinstance(embeds[index], list):
				if index == len(embeds) - 1:
					embeds[index][sub_index].set_footer(text='Last Page! You\'ve reached the end')
				await msg.edit(embed=embeds[index][sub_index])
			else:
				if index == len(embeds) - 1:
					embeds[index].set_footer(text='Last Page! You\'ve reached the end')
				await msg.edit(embed=embeds[index])
			await msg.remove_reaction(reaction, ctx.author)

def setup(bot):
	bot.add_cog(Ranking(bot))
