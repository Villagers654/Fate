from discord.ext import commands
import discord
import os

class customclass:
	def __init__(self, bot):
		self.bot = bot

	def luck(ctx):
		return ctx.message.author.id == 264838866480005122

# ~== Test ==~

	@commands.command()
	@commands.check(luck)
	async def cogs_log(self, ctx):
		await ctx.send('working')

# ~== Main ==~

	@commands.command(name='archive')
	@commands.has_permissions(manage_messages=True)
	@commands.cooldown(1, 120, commands.BucketType.channel)
	async def archive(self, ctx, amount:int):
		if amount > 1000:
			await ctx.send('You cannot go over 1000')
		else:
			async with ctx.typing():
				log = ""
				async for msg in ctx.channel.history(limit=amount):
					log += f"""{msg.author.name}: {msg.content}\n"""
				ctx.channel.name = ctx.channel.name.replace(" ", "-")
				f = open(f'/home/luck/FateZero/data/{ctx.channel.name}.txt', 'w')
				f.write(log)
				f.close()
				path = os.getcwd() + f"/data/{ctx.channel.name}.txt"
				await ctx.send(file=discord.File(path))
				os.system(f'rm data/{ctx.channel.name}.txt')

# ~== Pings ==~

def setup(bot):
	bot.add_cog(customclass(bot))
