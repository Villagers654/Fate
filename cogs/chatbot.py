from discord.ext import commands
from utils import checks, colors
from os.path import isfile
import discord
import asyncio
import random
import time
import json

class ChatBot:
	def __init__(self, bot):
		self.bot = bot
		self.toggle = {}
		self.cache = {}
		self.prefixes = {}
		self.cd = {}
		if isfile("./data/userdata/chatbot.json"):
			with open("./data/userdata/chatbot.json", "r") as infile:
				dat = json.load(infile)
				if "prefixes" in dat and "cache" in dat and "prefixes" in dat:
					self.toggle = dat["toggle"]
					self.cache = dat["cache"]
					self.prefixes = dat["prefixes"]

	def save(self):
		with open("./data/userdata/chatbot.json", "w") as outfile:
			json.dump({"toggle": self.toggle, "cache": self.cache, "prefixes": self.prefixes},
			          outfile, sort_keys=True, indent=4, separators=(',', ': '))

	@commands.group(name="chatbot")
	@commands.has_permissions(manage_messages=True)
	async def _chatbot(self, ctx):
		if not ctx.invoked_subcommand:
			guild_id = str(ctx.guild.id)
			toggle = "disabled"
			cache = "guilded"
			if guild_id in self.toggle:
				toggle = "enabled"
				cache = self.toggle[guild_id]
			e = discord.Embed(color=colors.fate())
			e.set_author(name="| Chat Bot", icon_url=ctx.author.avatar_url)
			e.set_thumbnail(url=self.bot.user.avatar_url)
			e.description = f"**Current Status:** {toggle}\n" \
				f"**Cache Location:** {cache}\n"
			e.add_field(name="◈ Usage ◈", value=f".chatbot enable\n"
				f"`enables chatbot`\n"
				f".chatbot disable\n"
				f"`disables chatbot`\n"
				f".chatbot swap_cache\n"
				f"`swaps to global or guilded cache`\n"
				f".chatbot clear_cache\n"
				f"`clears guilded cache`",
			inline=False)
			e.set_footer(text="Disabling chatbot resets cache location")
			await ctx.send(embed=e)

	@_chatbot.command(name="enable")
	@commands.has_permissions(manage_messages=True)
	async def _enable(self, ctx):
		guild_id = str(ctx.guild.id)
		if guild_id not in self.toggle:
			self.toggle[guild_id] = "guilded"
			await ctx.send("Enabled chatbot")
			return self.save()
		await ctx.send("Chatbot is already enabled")

	@_chatbot.command(name="disable")
	@commands.has_permissions(manage_messages=True)
	async def _disable(self, ctx):
		guild_id = str(ctx.guild.id)
		if guild_id not in self.toggle:
			await ctx.send("Chatbot is not enabled")
		del self.toggle[guild_id]
		self.save()
		await ctx.send("Disabled chatbot")

	@_chatbot.command(name="swap_cache")
	@commands.has_permissions(manage_messages=True)
	async def _swap_cache(self, ctx):
		guild_id = str(ctx.guild.id)
		if guild_id not in self.toggle:
			return await ctx.send("Chatbot needs to be "
			    "enabled in order for you to use this command")
		if self.toggle[guild_id] == "guilded":
			self.toggle[guild_id] = "global"
		else:
			self.toggle[guild_id] = "guilded"
		await ctx.send(f"Swapped cache location to {self.toggle[guild_id]}")
		self.save()

	@_chatbot.command(name="clear_cache")
	@commands.has_permissions(manage_messages=True)
	async def _clear_cache(self, ctx):
		guild_id = str(ctx.guild.id)
		if guild_id not in self.cache:
			return await ctx.send("No cached data found")
		del self.cache[guild_id]
		await ctx.send("Cleared cache")
		self.save()

	@commands.command(name="pop")
	@commands.check(checks.luck)
	async def _pop(self, ctx, *, phrase):
		guild_id = str(ctx.guild.id)
		for response in self.cache[guild_id]:
			if phrase in response:
				self.cache.pop(self.cache[guild_id].index(response))
		await ctx.message.delete()

	@commands.command(name="globalpop")
	@commands.check(checks.luck)
	async def _globalpop(self, ctx, *, phrase):
		for response in self.cache["global"]:
			if phrase in response:
				self.cache["global"].pop(self.cache["global"].index(response))
		await ctx.message.delete()

	@commands.command(name="prefixes")
	async def _prefixes(self, ctx):
		guild_id = str(ctx.guild.id)
		await ctx.send(self.prefixes[guild_id])

	@commands.command(name="delprefix")
	@commands.check(checks.luck)
	async def _delprefix(self, ctx, prefix):
		guild_id = str(ctx.guild.id)
		self.prefixes[guild_id].pop(self.prefixes[guild_id].index(prefix))
		await ctx.message.delete()

	async def on_message(self, m: commands.clean_content):
		if not m.author.bot:
			guild_id = str(m.guild.id)
			found = None
			if m.content.startswith("<@506735111543193601>"):
				return
			if "help" in m.content[:8]:
				if guild_id not in self.prefixes:
					self.prefixes[guild_id] = []
				if m.content[:m.content.find("help")] not in self.prefixes[guild_id]:
					self.prefixes[guild_id].append(m.content[:m.content.find("help")])
				return
			if guild_id in self.toggle:
				if len(m.content) is 0:
					return
				if guild_id not in self.cd:
					self.cd[guild_id] = 0
				if self.cd[guild_id] > time.time():
					return
				self.cd[guild_id] = time.time() + 2
				if guild_id in self.prefixes:
					for prefix in self.prefixes[guild_id]:
						if m.content.startswith(prefix):
							return
				if m.content.startswith("."):
					return
				key = random.choice(m.content.split(" "))
				cache = self.cache["global"]
				if guild_id not in self.cache:
					self.cache[guild_id] = []
				if self.toggle[guild_id] == "guilded":
					cache = self.cache[guild_id]
					if m.content not in cache:
						self.cache[guild_id].append(m.content)
						self.cache["global"].append(m.content)
						self.save()
				else:
					if m.content not in cache:
						self.cache["global"].append(m.content)
						self.save()
				matches = []
				for msg in cache:
					if key in msg:
						matches.append(msg)
						found = True
				if found:
					choice = random.choice(matches)
					if choice.lower() == m.content.lower():
						return
					async with m.channel.typing():
						await asyncio.sleep(1)
					await m.channel.send(choice)

def setup(bot):
	bot.add_cog(ChatBot(bot))
