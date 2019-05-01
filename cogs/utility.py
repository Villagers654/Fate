from discord.ext import commands
from datetime import datetime
from utils import colors
import discord
import aiohttp
import asyncio

class Utility(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.find = {}

	@commands.command()
	async def channelinfo(self, ctx, channel=None):
		if channel is None:
			ctx.channel = ctx.channel
		else:
			ctx.channel = channel
		fmt = "%m/%d/%Y"
		created = datetime.date(ctx.channel.created_at)
		e=discord.Embed(description="id: {}".format(ctx.channel.id), color=0x0000ff)
		e.set_author(name="{}:".format(ctx.channel.name), icon_url=ctx.author.avatar_url)
		e.set_thumbnail(url=ctx.guild.icon_url)
		e.add_field(name="◈ Main ◈", value="• Category: {}\n• Slowmode: {}".format(ctx.channel.category, ctx.channel.slowmode_delay), inline=False)
		e.add_field(name="◈ Topic ◈", value=ctx.channel.topic, inline=False)
		e.add_field(name="◈ Created ◈", value=created.strftime(fmt), inline=False)
		await ctx.send(embed=e)

	@commands.command()
	async def servericon(self, ctx):
		e=discord.Embed(color=0x80b0ff)
		e.set_image(url=ctx.guild.icon_url)
		await ctx.send(embed=e)

	@commands.command()
	async def serverinfo(self, ctx):
		fmt = "%m/%d/%Y"
		created = datetime.date(ctx.guild.created_at)
		e=discord.Embed(description="id: {0}\nOwner: {1}".format(ctx.guild.id, ctx.guild.owner.name), color=0x0000ff)
		e.set_author(name="{0}:".format(ctx.guild.name), icon_url=ctx.guild.owner.avatar_url)
		e.set_thumbnail(url=ctx.guild.icon_url)
		e.add_field(name="◈ Main", value="• AFK Timeout [{}]\n• Region [{}]\n• Members [{}]".format(ctx.guild.afk_timeout, ctx.guild.region, ctx.guild.member_count), inline=False)
		e.add_field(name="◈ Security", value="• Explicit Content Filter: [{0}]\n• Verification Level: [{1}]\n• 2FA Level: [{2}]".format(ctx.guild.explicit_content_filter, ctx.guild.verification_level, ctx.guild.mfa_level), inline=False)
		e.add_field(name="◈ Created", value=created.strftime(fmt), inline=False)
		await ctx.send(embed=e)

	@commands.command(name="userinfo", aliases=["stalk"])
	async def userinfo(self, ctx, *, member: discord.Member=None):
		if member is None:
			member = ctx.author
		perms = ', '.join(perm for perm, value in member.guild_permissions if value)
		e=discord.Embed(description="id: {}".format(member.id), color=member.color)
		e.set_author(name="{}:".format(member.name), icon_url=member.avatar_url)
		e.set_thumbnail(url=member.avatar_url)
		e.add_field(name="◈ Main ◈", value="• Nickname [{}]\n• Activity [{}]\n• Status [{}]\n• role [{}]".format(member.nick, member.activity, member.status, member.top_role), inline=False)
		e.add_field(name="◈ Perms ◈", value="```{}```".format(perms), inline=False)
		e.add_field(name="◈ Created ◈", value=datetime.date(member.created_at).strftime("%m/%d/%Y"), inline=False)
		await ctx.send(embed=e)

	@commands.command(name="roleinfo")
	async def _roleinfo(self, ctx, role_name: commands.clean_content):
		role_name = role_name.replace("@", "").lower()
		role = None
		for r in ctx.guild.roles:
			if r.name.lower() == role_name:
				role = r
		if role is None:
			for r in ctx.guild.roles:
				if role_name in r.name.lower():
					role = r
		if role is None:
			return await ctx.send("Role not found")
		fmt = "%m/%d/%Y"
		created = datetime.date(role.created_at)
		perms = ', '.join(perm for perm, value in role.permissions if value)
		e = discord.Embed(color=role.color)
		e.set_author(name=f"{role.name}:", icon_url=ctx.guild.icon_url)
		e.set_thumbnail(url=ctx.guild.icon_url)
		e.description = f"ID: {role.id}"
		e.add_field(name="◈ Main ◈", value=f"**Members:** [{len(list(role.members))}]\n"
		f"**Color:** [{role.color}]\n"
		f"**Mentionable:** [{role.mentionable}]\n"
		f"**Integrated:** [{role.managed}]\n"
		f"**Position:** [{role.position}]\n", inline=False)
		e.add_field(name="◈ Perms ◈", value=f"```{perms}```", inline=False)
		e.add_field(name="◈ Created ◈", value=created.strftime(fmt), inline=False)
		await ctx.send(embed=e)

	@commands.command(name='makepoll', aliases=['mp'])
	@commands.cooldown(1, 5, commands.BucketType.channel)
	@commands.has_permissions(manage_messages=True)
	async def makepoll(self, ctx):
		c = 0
		async for msg in ctx.channel.history(limit=3):
			if c == 1:
				await msg.add_reaction(':approve:506020668241084416')
				await msg.add_reaction(':unapprove:506020690584010772')
				await ctx.message.delete()
				break;
			c += 1

	@commands.command(name='members', aliases=['membercount'])
	@commands.bot_has_permissions(embed_links=True)
	async def members(self, ctx):
		humans = 0
		bots = 0
		online = 0
		for member in ctx.guild.members:
			if member.bot:
				bots += 1
			else:
				humans += 1
			status_array = [discord.Status.online, discord.Status.idle, discord.Status.dnd]
			if member.status in status_array:
				online += 1
		e = discord.Embed(color=colors.fate())
		e.set_author(name=f"Member Count", icon_url=ctx.guild.owner.avatar_url)
		e.set_thumbnail(url=ctx.guild.icon_url)
		e.description = f'**Total:** [`{len(ctx.guild.members)}`]\n' \
			f'**Online:** [`{online}`]\n' \
			f'**Humans:** [`{humans}`]\n' \
			f'**Bots:** [`{bots}`]'
		await ctx.send(embed=e)

	@commands.command()
	async def tinyurl(self, ctx, *, link: str):
		await ctx.message.delete()
		url = 'http://tinyurl.com/api-create.php?url=' + link
		async with aiohttp.ClientSession() as sess:
			async with sess.get(url) as resp:
				r = await resp.read()
				r = str(r).replace("b'", "").replace("'", "")
		emb = discord.Embed(color=0x80b0ff)
		emb.add_field(name="Original Link", value=link, inline=False)
		emb.add_field(name="Shortened Link", value=r, inline=False)
		emb.set_footer(text='Powered by tinyurl.com', icon_url='http://cr-api.com/static/img/branding/cr-api-logo.png')
		await ctx.send(embed=emb)

	@commands.command()
	async def avatar(self, ctx, *, member: discord.Member=None):
		try:
			if member is None:
				member = ctx.author
			e=discord.Embed(color=0x80b0ff)
			e.set_image(url=member.avatar_url)
			await ctx.send("◈ {}'s avatar ◈".format(member), embed=e)
		except Exception as e:
			await ctx.send(f'**```ERROR: {type(e).__name__} - {e}```**')

	@commands.command()
	async def owner(self, ctx):
		await ctx.send(ctx.guild.owner.name)

	@commands.command()
	async def topic(self, ctx):
		await ctx.send("{}".format(ctx.channel.topic))

	@commands.command(name='color')
	async def color(self, ctx, hex=None):
		if hex:
			hex = hex.replace('#', '')
			e = discord.Embed(color=eval(f"0x{hex}"))
			await ctx.send(embed=e)
		else:
			color = colors.random()
			e = discord.Embed(color=color)
			e.set_author(name=f"#{color}", icon_url=ctx.author.avatar_url)
			await ctx.send(embed=e)

	@commands.command(name="timer", pass_context=True, aliases=['reminder', 'alarm'])
	async def _timer(self, ctx, time, *, remember: commands.clean_content = ""):
		if "d" in time:
			t = int(time.replace("d", "")) * 60 * 60 * 24
		if "h" in time:
			t = int(time.replace("h", "")) * 60 * 60
		if "m" in time:
			t = int(time.replace("m", "")) * 60
		r = time.replace("m", " minutes").replace("1 minutes", "1 minute")
		r = r.replace("h", " hours").replace("1 hours", "1 hour")
		r = r.replace("d", " days").replace("1 days", "1 day")
		if not remember:
			await ctx.send(f"{ctx.author.name}, you have set a timer for {r}")
			await asyncio.sleep(float(t))
			await ctx.send(f"{ctx.author.name}, your timer for {r} has expired!")
		else:
			await ctx.send(f"{ctx.message.author.mention}, I will remind you about `{remember}` in {r}")
			await asyncio.sleep(float(t))
			await ctx.send(f"{ctx.message.author.mention}, your timer for {r} has expired! I was instructed to remind you about `{remember}`!")

	@commands.command(name="findmsg")
	@commands.cooldown(1, 5, commands.BucketType.channel)
	async def _findmsg(self, ctx, *, content=None):
		if content is None:
			e = discord.Embed(color=colors.fate())
			e.set_author(name="Error ⚠", icon_url=ctx.author.avatar_url)
			e.set_thumbnail(url=ctx.guild.icon_url)
			e.description = \
				"Content is a required argument\n" \
			    "Usage: `.find {content}`\n" \
				"Limit: 16,000"
			e.set_footer(text="Searches for a message")
			return await ctx.send(embed=e)
		async with ctx.typing():
			channel_id = str(ctx.channel.id)
			if channel_id in self.find:
				return await ctx.send("I'm already searching")
			self.find[channel_id] = True
			async for msg in ctx.channel.history(limit=25000):
				if ctx.message.id != msg.id:
					if content.lower() in msg.content.lower():
						e = discord.Embed(color=colors.fate())
						e.set_author(name="Message Found 🔍", icon_url=ctx.author.avatar_url)
						e.set_thumbnail(url=ctx.guild.icon_url)
						e.description = f"**Author:** `{msg.author}`\n" \
							f"[Jump to MSG]({msg.jump_url})"
						if msg.content != "":
							e.add_field(name="Full Content:", value=msg.content)
						if len(msg.attachments) > 0:
							for attachment in msg.attachments:
								e.set_image(url=attachment.url)
						await ctx.send(embed=e)
						del self.find[channel_id]
						return await ctx.message.delete()
		await ctx.send("Nothing found")
		del self.find[channel_id]

	@commands.command()
	async def poll(self, ctx, *, arg):
		e=discord.Embed(description=arg, color=0x80b0ff)
		e.set_author(name="| {} |".format(ctx.author.name), icon_url=ctx.author.avatar_url)
		message = await ctx.send(embed=e)
		await message.add_reaction(':approve:506020668241084416')
		await asyncio.sleep(0.5)
		await message.add_reaction(':unapprove:506020690584010772')
		await asyncio.sleep(0.5)
		await message.add_reaction('🤷')
		await ctx.message.delete()

	@commands.command()
	async def id(self, ctx, *, member: discord.Member=None):
		if member is None:
			member = ctx.author
		await ctx.send(member.id)

	@commands.command(name="channels")
	async def _channels(self, ctx):
		channels = ""
		for channel in ctx.guild.channels:
			channels += channel.name + "\n"
		await ctx.send(channels)

def setup(bot):
	bot.add_cog(Utility(bot))
