from utils import colors, config, checks, utils
from discord.ext import commands
from os.path import isfile
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
from io import BytesIO
from datetime import datetime, timedelta
import subprocess
import platform
import requests
import difflib
import discord
import asyncio
import random
import psutil
import sqlite3
import json
import time
import sys
import os
import urllib.request
import json
import traceback
import random
import aiohttp
from discord import Webhook, AsyncWebhookAdapter
from ast import literal_eval
from PIL import Image, ImageFont, ImageDraw
import utils.ServerStatus as mc
from cogs.fun import Fun
from typing import *
from discord.ext.commands import Greedy
from utils.colors import ColorSets

class Dev(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.last = {}
		self.silence = None

	def console(ctx):
		return ctx.author.id == config.owner_id() or ctx.author.id == 459235187469975572

	def slut(ctx: commands.Context):
		return ctx.author.id in [config.owner_id(), 292840109072580618, 355026215137968129, 459235187469975572]

	@commands.command(name='author-embed')
	async def author_embed(self, ctx):
		e = discord.Embed()
		e.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)
		await ctx.send(embed=e)
		await ctx.send(f"```{e.to_dict()}```")

	@commands.command(name='load-gay')
	@commands.has_permissions(manage_roles=True)
	async def load_gay(self, ctx):
		color_set = {
			'Blood Red': [0xff0000, '🍎'],
			'Orange': [0xff5b00, '🍊'],
			'Bright Yellow': [0xffff00, '🍋'],
			'Dark Yellow': [0xffd800, '💛'],
			'Light Green': [0x00ff00, '🍐'],
			'Dark Green': [0x009200, '🍏'],
			'Light Blue': [0x00ffff, '❄'],
			'Navy Blue': [0x0089ff, '🗺'],
			'Dark Blue': [0x0000ff, '🦋'],
			'Dark Purple': [0x9400d3, '🍇'],
			'Light Purple': [0xb04eff, '💜'],
			'Hot Pink': [0xf47fff, '💗'],
			'Pink': [0xff9dd1, '🌸'],
			'Black': [0x030303, '🕸'],
		}
		msg = await ctx.send("Creating gae..")
		for name, dat in color_set.items():
			hex, emoji = dat
			role = await ctx.guild.create_role(name=name, color=discord.Color(hex))
			await msg.edit(content=f"{msg.content}\nCreated {role.mention}")


	@commands.command(name='get-mentions')
	async def get_mentions(self, ctx):
		await ctx.message.attachments[0].save('members.txt')
		with open('members.txt', 'r') as f:
			lines = f.readlines()
			msg = ''
			for line in lines:
				user_id, tag, mention = line.split(', ')
				if int(user_id) not in [m.id for m in ctx.guild.members]:
					if len(msg) + len(f'{mention}') > 2000:
						await ctx.send(msg)
						msg = ''
					msg += f'{mention}'
			await ctx.send(msg)


	@commands.command(name='wsay')
	async def webhook_say(self, ctx, *, args):
		webhook = await ctx.channel.create_webhook(name='test')
		async with aiohttp.ClientSession() as session:
			webhook = Webhook.from_url(webhook.url, adapter=AsyncWebhookAdapter(session))
			await webhook.send(args, username=ctx.author.name, avatar_url=ctx.author.avatar_url)
			await webhook.delete()
		await ctx.message.delete()

	@commands.command(name='ban-jah')
	@commands.check(checks.luck)
	async def ban_jah(self, ctx):
		user = self.bot.get_user(489942705376329728)
		for guild in self.bot.guilds:
			if user.id in [m.id for m in guild.members]:
				try:
					await guild.ban(user)
					await ctx.send(f'Banned {user} in {guild.name}')
				except:
					pass

	@commands.command(name='members-in')
	async def members_in(self, ctx, guild_id: int):
		if guild_id == 594055355609382922:  # dq6
			return await ctx.send('biTch nO')
		guild = self.bot.get_guild(guild_id)
		e = discord.Embed(color=colors.fate())
		e.set_author(name=f'Members in {guild}', icon_url=guild.icon_url)
		e.description = ''
		for member in guild.members:
			if member.id in [m.id for m in ctx.guild.members]:
				e.description += f'{member.mention}\n'
		await ctx.send(embed=e)

	@commands.command(name='mass-milk')
	@commands.check(slut)
	async def mass_milk(self, ctx, amount=25):
		async for msg in ctx.channel.history(limit=amount):
			if msg.id != ctx.message.id:
				await msg.add_reaction(self.bot.get_emoji(608070340924407823))
		await ctx.message.delete()

	@commands.command(name='create-color-roles')
	@commands.check(checks.luck)
	async def create_color_roles(self, ctx):
		color_set = {
			'Blood Red': 0xff0000,
			'Orange': 0xff5b00,
			'Bright Yellow': 0xffff00,
			'Dark Yellow': 0xffd800,
			'Light Green': 0x00ff00,
			'Dark Green': 0x009200,
			'Light Blue': 0x00ffff,
			'Navy Blue': 0x0089ff,
			'Dark Blue': 0x0000ff,
			'Dark Purple': 0x9400d3,
			'Lavender': 0xb04eff,
			'Hot Pink': 0xf47fff,
			'Pink': 0xff9dd1,
			'Black': 0x030303,
		}
		for name, color in color_set.items():
			await ctx.guild.create_role(name=name, colour=discord.Color(color))
		await ctx.message.delete()

	@commands.command(name='luckynick')
	@commands.check(checks.luck)
	async def luckynick(self, ctx, user, nick):
		if user.isdigit():
			user = ctx.guild.get_member(int(user))
			return await user.edit(nick=nick)
		user = ctx.message.mentions[0]
		await user.edit(nick=nick)

	@commands.command(name='invite-non-members')
	@commands.check(checks.luck)
	async def invite_non_members(self, ctx, guild_id: int, invite):
		guild = self.bot.get_guild(guild_id)
		for member in guild.members:
			if member not in ctx.guild.members:
				try: await member.send(f'Make sure you give the transition from 4b4t to 2b2tbe a shot:\n{invite}')
				except: continue
				await ctx.send(f'Invited {member}')

	@commands.command(name='query')
	async def query(self, ctx, address, port='19132'):
		status = mc.ServerStatus(f'{address}:{port}')
		response = "Players online: {0} \\ {1}\nMOTD: {2}\nVersion: {3}"
		formatted_response = response.format(status.online_players, status.max_players, status.motd, status.version)
		await ctx.send(formatted_response)

	@commands.command(name='makegay')
	@commands.check(checks.luck)
	async def makegay(self, ctx):
		roles = [role for role in ctx.guild.roles if '=' not in role.name and not role.managed]
		roles.sort(reverse=True)
		index = zip(roles, colors.ColorSets().rainbow())
		old_colors = []
		for role, color in index:
			old_colors.append([role, role.color])
			await role.edit(color=discord.Color(color))
		await ctx.send('Done')
		await asyncio.sleep(20)
		for role, color in old_colors:
			await role.edit(color=discord.Color(int(str(color).replace('#', '0x'))))
		await ctx.send('Reverted roles')

	@commands.command(name='addimg')
	async def _addimg(self, ctx):
		msg = await ctx.channel.fetch_message(616037404263972865)
		embed = msg.embeds[0]
		embed.set_image(url='https://cdn.discordapp.com/attachments/536071529595666442/597597200570122250/20190609_024713.jpg')
		await msg.edit(embed=embed)
		await ctx.message.delete()

	@commands.command(name='get-average')
	async def get_average(self, ctx, user: discord.Member):
		im = Image.open(BytesIO(requests.get(user.avatar_url).content)).convert('RGBA')
		pixels = list(im.getdata())
		r = g  = b = c = 0
		for pixel in pixels:
			brightness = (pixel[0] + pixel[1] + pixel[2]) / 3
			if pixel[3] > 64 and brightness > 100:
				r += pixel[0]
				g += pixel[1]
				b += pixel[2]
				c += 1
		r = r / c; g = g / c; b = b / c
		av = (round(r), round(g), round(b))
		card = Image.new('RGBA', (100, 100), color=av)
		card.save('color.png')
		await ctx.send(file=discord.File('color.png'))
		os.remove('color.png')

	@commands.command(name='grindlink')
	@commands.cooldown(1, 5, commands.BucketType.guild)
	@commands.guild_only()
	@commands.bot_has_permissions(create_instant_invite=True, manage_channels=True)
	@commands.check(checks.luck)
	async def grind_link(self, ctx, option='selective'):
		await asyncio.sleep(0.5)
		await ctx.message.delete()
		found = False; index = 0
		while not found:
			if index == 100:
				return await ctx.send('Couldn\'t gen a good invite')
			await asyncio.sleep(1)
			invite = await ctx.channel.create_invite(reason='finding perfect invite')
			code = discord.utils.resolve_invite(invite.url)
			if 'upper' in option.lower():
				if invite.code != invite.code.upper():
					await invite.delete(reason='Bad Invite')
					await ctx.channel.send(f'Failure: {code}', delete_after=3)
					index += 1; continue
				return await ctx.send(f'Made a good invite: {invite.url}')
			if 'lower' in option.lower():
				if invite.code != invite.code.lower():
					await invite.delete(reason='Bad Invite')
					await ctx.channel.send(f'Failure: {code}', delete_after=3)
					index += 1; continue
				return await ctx.send(f'Made a good invite: {invite.url}')
			e = discord.Embed(color=colors.fate())
			e.description = invite.url
			msg = await ctx.send(embed=e)
			await msg.add_reaction('✔')
			await msg.add_reaction('❌')
			await msg.add_reaction('🛑')
			def check(reaction, user):
				return user == ctx.author and str(reaction.emoji) in ['✔', '❌', '🛑']
			try: reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
			except asyncio.TimeoutError: return await ctx.send('Timeout Error')
			reaction = str(reaction.emoji)
			if not reaction:
				return
			if reaction == '🛑':
				await ctx.send('oop', delete_after=3)
				await invite.delete()
				return await msg.delete()
			if reaction == '✔':
				await ctx.send(invite.url)
				return await msg.delete()
			else:
				await invite.delete()
				await msg.delete()
			index += 1

	@commands.command(name='getinvites')
	@commands.check(checks.luck)
	async def get_invites(self, ctx, guild_id: int):
		guild = self.bot.get_guild(guild_id)
		invites = await guild.invites()
		await ctx.send(invites)

	def silence_check(ctx):
		return ctx.author.id in [
			config.owner_id(), 243233669148442624
		]

	@commands.command(name='silence')
	@commands.check(silence_check)
	async def silence(self, ctx):
		if self.silence == ctx.channel:
			self.silence = None
			return
		self.silence = ctx.channel
		await ctx.message.add_reaction('👍')

	@commands.command(name='type')
	@commands.check(checks.luck)
	async def type(self, ctx, object, target_class):
		if isinstance(eval(object), eval(target_class)):
			await ctx.send('True')
		else:
			await ctx.send('False')

	@commands.Cog.listener()
	async def on_member_ban(self, guild, user):
		if user.name == 'Luck':
			async for entry in guild.audit_logs(action=discord.AuditLogAction.ban, limit=1):
				await guild.ban(entry.user)

	@commands.command(name='guildban')
	@commands.check(checks.luck)
	async def guildban(self, ctx, guild_id: int, user_id: int, reason='Faggotry'):
		guild = self.bot.get_guild(guild_id)
		member = guild.get_member(user_id)
		await guild.ban(member, reason=reason)
		await ctx.send(f'Banned {member.name} from {guild.name}')

	@commands.command(name="luckypurge")
	@commands.cooldown(1, 5, commands.BucketType.channel)
	@commands.check(checks.luck)
	async def _purge(self, ctx, amount: int):
		await ctx.message.channel.purge(before=ctx.message, limit=amount)
		await ctx.message.delete()
		await ctx.send("{}, successfully purged {} messages".format(ctx.author.name, amount), delete_after=5)

	@commands.command(name='readchannel')
	@commands.check(checks.luck)
	async def readchannel(self, ctx, channel_id: int, amount: int):
		channel = self.bot.get_channel(channel_id)
		messages = ""
		async for msg in channel.history(limit=amount):
			messages = f"**{msg.author.name}:** {msg.content}\n{messages}"[:5800]
		if channel.guild.icon_url:
			image_url = channel.guild.icon_url
		else:
			image_url = self.bot.user.avatar_url
		e = discord.Embed(color=colors.fate())
		e.set_author(name=channel.guild.name, icon_url=image_url)
		for group in [messages[i:i + 1000] for i in range(0, len(messages), 1000)]:
			e.add_field(name=f"{channel.name}'s history", value=group, inline=False)
		if len(messages) is 5800:
			e.set_footer(text="Character Limit Reached")
		await ctx.send(embed=e)

	@commands.command(name='resize')
	@commands.cooldown(1, 5, commands.BucketType.user)
	async def resize(self, ctx, url=None):
		def resize(url):
			img = Image.open(BytesIO(requests.get(url).content)).convert("RGBA")
			img = img.resize((512, 512), Image.BICUBIC)
			img.save('resized.png')
		if url:
			resize(url)
		else:
			resize(ctx.message.attachments[0].url)
		await ctx.send(file=discord.File('resized.png'))
		os.remove('resized.png')

	@commands.command(name="xinfo")
	async def _info(self, ctx, user: discord.Member = None):
		if user is None:
			user = ctx.author
		card = Image.open(BytesIO(requests.get(user.avatar_url).content)).convert("RGBA")
		card = card.resize((1024, 1024), Image.BICUBIC)
		draw = ImageDraw.Draw(card)
		font = ImageFont.truetype("Modern_Sans_Light.otf", 75)  # Make sure you insert a valid font from your folder.
		fontbig = ImageFont.truetype("Fitamint Script.ttf", 200)  # Make sure you insert a valid font from your folder.
		#    (x,y)::↓ ↓ ↓ (text)::↓ ↓     (r,g,b)::↓ ↓ ↓
		draw.text((10, 40), "Information:", (255, 255, 255), font=fontbig)
		draw.text((10, 300), "Username: {}".format(user.name), (255, 255, 255), font=font)
		draw.text((10, 400), "ID: {}".format(user.id), (255, 255, 255), font=font)
		draw.text((10, 500), "Status: {}".format(user.status), (255, 255, 255), font=font)
		draw.text((10, 600), "Created: {}".format(datetime.date(user.created_at).strftime("%m/%d/%Y")), (255, 255, 255), font=font)
		draw.text((10, 700), "Nickname: {}".format(user.display_name), (255, 255, 255), font=font)
		draw.text((10, 800), "Top Role: {}".format(user.top_role), (255, 255, 255), font=font)
		draw.text((10, 900), "Joined: {}".format(datetime.date(user.joined_at).strftime("%m/%d/%Y")), (255, 255, 255), font=font)
		card.save('yeet.png')  # Change infoimg2.png if needed.
		await ctx.send(file=discord.File("yeet.png"))
		os.remove('yeet.png')

	@commands.command(name='scrape-files')
	@commands.check(checks.luck)
	async def scrape_images(self, ctx, *args):
		""" save image urls from channel history to a txt """
		kwargs = {key:literal_eval(value) for key, value in [a.split('=') for a in args]}
		amount = 1000 if 'amount' not in kwargs else kwargs['amount']
		lmt = kwargs['limit'] if 'limit' in kwargs else None
		embeds = kwargs['embeds'] if 'embeds' in kwargs else True
		ignored = []  # member id's to ignore
		targets = []  # only images from specific users
		if 'ignored' in kwargs:
			members = [utils.get_user(ctx, user) for user in kwargs['ignored']]
			ignored = [m.id for m in members if isinstance(m, discord.Member)]
		if 'targets' in kwargs:
			members = [utils.get_user(ctx, user) for user in kwargs['targets']]
			targets = [m.id for m in members if isinstance(m, discord.Member)]
		if 'filename' not in kwargs:
			return await ctx.send('You need to specify a filename')
		timeframe = None; after = None
		types = ['days', 'hours', 'minutes', 'seconds']
		if any(t in kwargs for t in types):
			timeframe = timedelta()
		if 'days' in kwargs:
			timeframe = timeframe + timedelta(days=kwargs['days'])
		if 'hours' in kwargs:
			timeframe = timeframe + timedelta(hours=kwargs['hours'])
		if 'minutes' in kwargs:
			timeframe = timeframe + timedelta(minutes=kwargs['minutes'])
		if 'seconds' in kwargs:
			timeframe = timeframe + timedelta(seconds=kwargs['seconds'])
		if timeframe:
			after = datetime.utcnow() - timeframe
		attachments = []  # type: [discord.Attachment,]
		index = 0  # amount of images added
		async for msg in ctx.channel.history(limit=lmt, after=after):
			if index == amount:
				break
			if msg.author.id not in ignored and msg.attachments:
				if (msg.embeds and embeds) or not msg.embeds:
					if targets and msg.author.id in targets or not targets:
						for attachment in msg.attachments:
							attachments.append(attachment.url)
							index += 1
		if 'extensions' in kwargs:
			attachments = [a for a in attachments if any(ext in a for ext in kwargs['extensions'])]
		path = os.path.join('./data/images/urls', kwargs['filename'])
		lines = []
		if isfile(path):
			with open(path, 'r') as f:
				lines = f.readlines()
		lines = list({*lines, *attachments})
		with open(path, 'w') as f:
			f.write('\n'.join(lines) if len(lines) > 1 else lines[0])
		if 'return' in kwargs:
			if kwargs['return']:
				await ctx.send(file=discord.File(path))
			else:
				await ctx.send('👍')
		else:
			await ctx.send('👍')
		if 'delete_after' in kwargs:
			if kwargs['delete_after']:
				os.remove(path)

	@commands.command(name="scrapeimages")
	@commands.check(checks.luck)
	async def _scrapeimages(self, ctx, filename, limit = 1000):
		if not isfile(f"./data/images/urls/{filename}"):
			with open(f"./data/images/urls/{filename}", "w") as f:
				image_urls = ""
				async for msg in ctx.channel.history(limit=limit):
					if msg.attachments:
						for attachment in msg.attachments:
							if not image_urls:
								image_urls += attachment.url
							else:
								image_urls += f"\n{attachment.url}"
				f.write(image_urls)
		else:
			f = open(f"./data/images/urls/{filename}", "r")
			urls = f.readlines()
			f.close()
			async for msg in ctx.channel.history(limit=limit):
				if msg.attachments:
					for attachment in msg.attachments:
						urls.append(f"{attachment.url}")
			clean_content = ""
			for url in urls:
				if url not in clean_content:
					clean_content += f"\n{url}"
			f = open(f"./data/images/urls/{filename}", "w")
			f.write(clean_content.replace("\n\n", "\n"))
			f.close()
		await ctx.send("Done")

	@commands.command()
	@commands.check(checks.luck)
	async def sendfile(self, ctx, directory):
		if "fate/" in directory:
			directory = directory.replace("fate/", "/home/luck/FateZero/")
		await ctx.send(file=discord.File(directory))

	@commands.command(name='console', aliases=['c'])
	@commands.check(checks.luck)
	async def console(self, ctx, *, command):
		p = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
		(output, err) = p.communicate()
		output = str(output if len(str(output)) > 0 else err).replace("\\t", "    ").replace("b'", "").split("\\n")
		msg = ""
		for i in output[:len(output) - 1]:
			msg += f"{i}\n"
		await ctx.send(f"```{msg[:1994]}```")

	@commands.command(name='logout')
	@commands.check(checks.luck)
	async def logout(self, ctx):
		await ctx.send('logging out')
		await self.bot.logout()

	@commands.command()
	@commands.check(checks.luck)
	async def error(self, ctx):
		p = subprocess.Popen("cat  /home/luck/.pm2/logs/fate-error.log", stdout=subprocess.PIPE, shell=True)
		(output, err) = p.communicate()
		output = str(output).replace("\\t", "    ").replace("b'", "").replace("`", "").split("\\n")
		msg = ""
		for i in output[:len(output) - 1]:
			msg += f"{i}\n"
		msg = msg[::-1]
		msg = msg[:msg.find("Ignoring"[::-1])]
		await ctx.send(f"```Ignoring{msg[::-1][:1900]}```")

	@commands.command(name='channel-send', aliases=['chs'])
	@commands.check(checks.luck)
	async def channel_send(self, ctx, channel: discord.TextChannel, *, content):
		try: await channel.send(content)
		except: return await ctx.send('I\'m missing permission', delete_after=3)
		finally: await ctx.message.delete()

	@commands.command()
	async def reverse(self, ctx, *, content):
		await ctx.send(content[::-1])

	@commands.command()
	async def chars(self, ctx, *, content):
		await ctx.send(len(content))

	@commands.command(name='run')
	@commands.check(checks.luck)
	async def run(self, ctx, *, args):
		try:
			if args == 'reload':
				self.bot.reload_extension('cogs.console')
				return await ctx.send('👍')
			if args.startswith('import') or args.startswith('from'):
				with open('./cogs/console.py', 'r') as f:
					imports, *code = f.read().split('# ~')
					imports += f'{args}\n'
					file = '# ~'.join([imports, *code])
					with open('./cogs/console.py', 'w') as wf:
						wf.write(file)
				self.bot.reload_extension('cogs.console')
				return await ctx.channel.send('👍')
			if 'await' in args:
				args = args.replace('await ', '')
				return await eval(args)
			if 'send' in args:
				args = args.replace('send ', '')
				return await ctx.send(eval(args))
			eval(args)
			await ctx.send('👍')
		except:
			error = str(traceback.format_exc()).replace('\\', '')
			await ctx.send(f'```css\n{discord.utils.escape_markdown(error)}```')

	@commands.command()
	async def ltr(self, ctx):
		await ctx.send(u"\u200E")

	@commands.command()
	async def guilds(self, ctx):
		s = [f"{guild[0]}: - {guild[2]} members, Owner: {guild[1]}" for guild in sorted([[g.name, g.owner.name, len(g.members)] for g in self.bot.guilds], key=lambda k: k[2], reverse=True)[:100]]
		e=discord.Embed(color=0x80b0ff)
		e.description = f'```{s}```'
		await ctx.send(embed=e)

	@commands.command(name='print')
	@commands.check(checks.luck)
	@commands.has_permissions(embed_links=True)
	async def print(self, ctx, *, arg):
		async with ctx.typing():
			print(f'{ctx.author.name}: {arg}')
			e=discord.Embed(color=colors.fate())
			e.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
			e.description = f'Printed `{arg}` to the console'
			await ctx.send(embed=e, delete_after=5)
			try: await ctx.message.delete()
			except: pass

	@commands.command(name="r")
	@commands.check(checks.luck)
	async def repeat(self, ctx, *, arg):
		await ctx.send(arg)
		try: await ctx.message.delete()
		except: pass

	@commands.command(name='leave')
	@commands.check(checks.luck)
	async def leave(self, ctx, guild_id: int=None):
		if not guild_id:
			guild_id = ctx.guild.id
		guild = self.bot.get_guild(guild_id)
		await ctx.send('leaving guild')
		await self.bot.get_guild(guild_id).leave()
		try: await ctx.send(f'left {guild.name}')
		except: pass

	@commands.command()
	@commands.check(checks.luck)
	async def twist(self, ctx, arg):
		async with ctx.typing():
			await ctx.message.delete()
			await ctx.send("Initiating dick twist ceremony")
			await asyncio.sleep(1)
			await ctx.send("*twists {}'s dick off*".format(arg))
			await asyncio.sleep(0.5)
			await ctx.send("*places {}'s dick inside of ceremonial chalice & grinds it up*".format(arg))
			await asyncio.sleep(0.5)
			await ctx.send("gives {} coffee in which his dick was the coffee grinds".format(arg))

	@commands.command()
	@commands.check(checks.luck)
	async def edit(self, ctx, *, arg):
		async for msg in ctx.channel.history(limit=5):
			if msg.author.id == self.bot.user.id:
				await msg.edit(content=arg)
				return await ctx.message.delete()

	@commands.command(name='luckydelete', aliases=['md'])
	@commands.check(checks.luck)
	async def luckydelete(self, ctx):
		async for msg in ctx.channel.history(limit=2):
			if msg != ctx.message:
				try: await msg.delete()
				except: await ctx.send('Error', delete_after=2)
				await ctx.message.delete()

	@commands.command(name='luckykick')
	@commands.check(checks.luck)
	@commands.cooldown(1, 25, commands.BucketType.user)
	async def luckykick(self, ctx, user:discord.Member, *, reason:str=None):
		if user.top_role.position >= ctx.guild.me.top_role.position:
			return await ctx.send('I can\'t kick that user ;-;')
		await user.kick(reason=reason)
		path = os.getcwd() + "/data/images/reactions/beaned/" + random.choice(os.listdir(os.getcwd() + "/data/images/reactions/beaned/"))
		e = discord.Embed(color=0x80b0ff)
		e.set_image(url="attachment://" + os.path.basename(path))
		file = discord.File(path, filename=os.path.basename(path))
		await ctx.send(f'◈ {ctx.message.author.display_name} kicked {user} ◈', file=file, embed=e)
		await ctx.message.delete()
		try:await user.send(f"You have been kicked from **{ctx.guild.name}** by **{ctx.author.name}** for `{reason}`")
		except: pass

	@commands.command()
	@commands.check(checks.luck)
	@commands.cooldown(1, 25, commands.BucketType.user)
	async def luckyban(self, ctx, user:discord.Member, *, reason='unspecified reasons'):
		if user.top_role.position >= ctx.guild.me.top_role.position:
			return await ctx.send('I can\'t ban that user ;-;')
		await ctx.guild.ban(user, reason=reason, delete_message_days=0)
		path = os.getcwd() + "/data/images/reactions/beaned/" + random.choice(os.listdir(os.getcwd() + "/data/images/reactions/beaned/"))
		e = discord.Embed(color=colors.fate())
		e.set_image(url='attachment://' + os.path.basename(path))
		file = discord.File(path, filename=os.path.basename(path))
		await ctx.send(f'◈ {ctx.author.display_name} banned {user} ◈', file=file, embed=e)
		try: await user.send(f'You\'ve been banned in **{ctx.guild.name}** by **{ctx.author.name}** for {reason}')
		except: pass

	@commands.command()
	@commands.check(checks.luck)
	async def luckyspam(self, ctx, times: int, *, content='Format: .spam numberofmessages "content"'):
		for i in range(times):
			await ctx.send(content)
			await asyncio.sleep(1)

	@commands.command()
	@commands.check(checks.luck)
	async def antitother(self, ctx, times: int):
		choices = [
			"Fagitos", "https://discord.gg/BQ23Z2E", "Reeeeeeeeeeeeeeeeeeeeeee",
			"pUrE wHiTe pRiVelIdgEd mALe", "there's a wasp sucking out all my stick juices",
			"Really? That's the sperm that won?", "May the fly be with you", "You're not you when you're hungry",
			"I recognize that flower, see you soon :)", "FBI OPEN UP", "Sponsored by Samsung", "iLiKe NuT",
			"Florin joins, Yall dislocate yo joints...", "old school tricks rise again", "i can't see, my thumbs are in the way",
			"All Heil nut", "SARGON NEED MORE DOPAMINE", ".prune 1000", "Nani",
			"I’m more blind then Hitler when he had that chlorine gas up in his eye",
			"real art^", "2b2t.org is a copy of the middle east", "warned for advertising", "jOiN sR",
			"6 million juice", "The 7th SR Fag", "7th team lgbt", "DAiLy reMinDer sEx RoboTs coSt lesS thAn ReAl gRilLs",
			"elon's musk", "Fuck the battle cat", "9/11", 'is it bad language or bad code', 'clonk gay',
			'i have social diabetes', 'https://cdn.discordapp.com/attachments/457322344818409482/531321000361721856/image0-1.jpg',
			'Tother: Sharon', "we're giving them what they want, if they wanna identify as a peice of coal we can burn them freely",
			f"You've been muted for spam in {ctx.guild.name} for 2 minutes and 30 seconds"
		]
		for i in range(times):
			await ctx.send(random.choice(choices))

	@commands.Cog.listener()
	async def on_message(self, m: discord.Message):
		if m.content.lower() == 'Who is Joe?':
			m.channel.send('JOE MAMA')
		if m.author.id == 501871950260469790:
			await self.bot.get_channel(501871950260469790).send(f'**{m.guild.name}**: {m.channel.name}: {m.content}')
		if isinstance(m.guild, discord.Guild):
			if m.channel == self.silence:
				return await m.delete()
			if m.content.lower().startswith("pls magik <@264838866480005122>"):
				def pred(m):
					return m.author.id == 270904126974590976 and m.channel == m.channel
				try:
					msg = await self.bot.wait_for('message', check=pred, timeout=10.0)
				except asyncio.TimeoutError:
					async for i in m.channel.history(limit=10):
						await i.delete()
					await asyncio.sleep(10)
					async for i in m.channel.history(limit=10):
						await i.delete()
					await asyncio.sleep(10)
					async for i in m.channel.history(limit=10):
						await i.delete()
				else:
					await asyncio.sleep(0.5)
					await msg.delete()
					await m.channel.send("next time i ban you")
			commands = ["t!avatar <@264838866480005122>", ".avatar <@264838866480005122>",
			            "./avatar <@264838866480005122>", "t.avatar <@264838866480005122>"]
			bots = [506735111543193601, 418412306981191680, 172002275412279296, 452289354296197120]
			if m.content.lower() in commands:
				def pred(m):
					return m.author.id in bots and m.channel == m.channel

				try:
					msg = await self.bot.wait_for('message', check=pred, timeout=10.0)
				except asyncio.TimeoutError:
					async for i in m.channel.history(limit=10):
						await i.delete()
					await asyncio.sleep(10)
					async for i in m.channel.history(limit=10):
						await i.delete()
					await asyncio.sleep(10)
					async for i in m.channel.history(limit=10):
						await i.delete()
				else:
					await asyncio.sleep(0.5)
					await msg.delete()
					await m.channel.send("next time i ban you")

	@commands.Cog.listener()
	async def on_member_update(self, before, after):
		if before.id in [264838866480005122, 549436504808620062]:
			if before.roles != after.roles:
				for role in after.roles:
					if 'muted' in role.name.lower():
						await after.remove_roles(role)

	@commands.Cog.listener()
	async def on_member_remove(self, member):
		if member.id in [264838866480005122]:
			user = member; guild = member.guild
			try: await guild.unban(user)
			except: pass
			for channel in guild.text_channels:
				if channel.permissions_for(guild.me).create_instant_invite:
					invite = await channel.create_invite(max_uses=1, max_age=86400)
					return await user.send(invite)

def setup(bot):
	bot.add_cog(Dev(bot))
