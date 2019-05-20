from discord.ext import commands
from utils import checks
import discord
import asyncio
import random

class System(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.output_log = ''
		self.error_log = ''

	async def console_task(self):
		while True:
			try:
				channel = self.bot.get_channel(577661412432805888)
				output_msg = await channel.fetch_message(577662410010263564)
				with open('/home/luck/.pm2/logs/fate-out.log', 'r') as f:
					new_log = f'```{f.read()[-1994:]}```'
					if new_log != self.output_log:
						self.output_log = new_log
						await output_msg.edit(content=new_log)
						await channel.send('updated clean console', delete_after=5)
				output_msg = await channel.fetch_message(577662416687595535)
				with open('/home/luck/.pm2/logs/fate-error.log', 'r') as f:
					new_log = f'```{discord.utils.escape_markdown(f.read())[-1994:]}```'
					if new_log != self.error_log:
						self.error_log = new_log
						await output_msg.edit(content=new_log)
						await channel.send('updated error console', delete_after=5)
				await asyncio.sleep(5)
			except Exception as e:
				try:
					await self.bot.get_channel(577661461543780382).send(e)
				except:
					pass
				await asyncio.sleep(5)

	@commands.command(name='save')
	@commands.check(checks.luck)
	async def save_file(self, ctx, filename=None):
		for attachment in ctx.message.attachments:
			if not filename:
				filename = attachment.filename
			await attachment.save(filename)
			await ctx.send('👍', delete_after=5)
			await asyncio.sleep(5)
			await ctx.message.delete()

	@commands.Cog.listener()
	async def on_ready(self):
		self.bot.loop.create_task(self.console_task())

	@commands.Cog.listener()
	async def on_message(self, msg):
		if msg.author.id == 264838866480005122:
			if 'chaoscontrol' in msg.content:
				chosen = []
				indexed = []
				bot = msg.guild.get_member(self.bot.user.id)
				async for m in msg.channel.history(limit=50):
					if m.author.top_role.position < bot.top_role.position:
						if m.author.id not in indexed:
							if random.randint(1, 2) == 1:
								chosen.append([m.author, m.author.display_name])
							indexed.append(m.author.id)
				succeeded = []
				for member, name in chosen:
					try:
						await member.edit(nick=('[Dead] ' + name)[:32])
						succeeded.append([member, name])
						await asyncio.sleep(1)
					except:
						pass
				kill_count = len(succeeded)
				await msg.channel.send(f'Killed {kill_count} {"user" if kill_count == 1 else "users"}')
				await asyncio.sleep(120)
				for member, name in succeeded:
					try:
						if member.nick:
							await member.edit(nick=name[:32])
						else:
							await member.edit(nick='')
					except:
						pass

def setup(bot):
	bot.add_cog(System(bot))
