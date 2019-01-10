from discord.ext import commands
from termcolor import colored, cprint
import traceback
import datetime
import discord
import asyncio
import random
import time

# ~== Core ==~

description = '''Fate[Zero]: Personal Bot'''
bot = commands.Bot(command_prefix='.', case_insensitive=True)
files = ['error_handler', 'owner', 'menus', 'core', 'mod', 'music', 'welcome', 'farewell', 'notes', 'archive', 'coffeeshop', 'custom', 'actions', 'reactions',
         'responses', 'textart', 'fun', 'math', 'dev', '4b4t', 'readme', 'legit', 'reload', 'embeds', 'manager', 'profiles', 'save']
bot.START_TIME = time.time()
bot.remove_command('help')
errorcount = 0
error = False

async def status_task():
	while True:
		await bot.change_presence(activity=discord.Game(name="4b4t.net | {}".format(random.choice(["FBI OPEN UP", "YEET to DELETE", "Pole-Man", "♡Juice wrld♡", "ANIMOO", "Mad cuz Bad", "Quest for Cake", "Gone Sexual"]))))
		await asyncio.sleep(15)
		await bot.change_presence(activity=discord.Game(name='4b4t.net | use .help'))
		await asyncio.sleep(15)
		await bot.change_presence(activity=discord.Game(name=f'4b4t.net | {len(list(bot.users))} users'))
		await asyncio.sleep(15)
		await bot.change_presence(activity=discord.Game(name=f'4b4t.net | {len(list(bot.guilds))} servers'))
		await asyncio.sleep(15)

@bot.event
async def on_ready():
	cprint('--------------------------', 'cyan')
	print('Logged in as')
	print(bot.user.name)
	print(bot.user.id)
	print(f'Extensions: {len(bot.extensions)}')
	print(f'Errors: {errorcount}')
	cprint('--------------------------', 'cyan')
	print(' ζξ Welcome back Mikey :)\n'
	      '┌──┬┐ The best way to start\n'
	      '│  ├┘ your day is with the\n'
	      '└──┘ blood of your enemys')
	cprint('--------------------------', 'cyan')
	fmt = "%m-%d-%Y %I:%M%p"
	created = datetime.datetime.now()
	cprint(created.strftime(fmt), 'yellow')
	if error is not False:
		await bot.get_channel(514213558549217330).send(f"```{error}```")
	bot.loop.create_task(status_task())

# ~== Startup ==~

if __name__ == '__main__':
	print("Loading cogs..")
	cogs = 0
	rank = 0
	f = None
	for cog in files:
		cogs += 1
		try:
			bot.load_extension("cogs." + cog)
			rank += 1
			cprint(f"{cogs}. Cogs: {cog} - operational", "green")
		except Exception as e:
			errorcount += 1
			cprint(f"{cogs}. Cogs: {cog} - error", "red")
			error = traceback.format_exc()
	if rank == cogs:
		cprint(f"Loaded {rank}/{cogs} cogs :)", "magenta")
	else:
		cprint(f"Loaded {rank}/{cogs} cogs :(", "magenta")
	cprint(f"Logging into discord..", "blue")
f = open("./data/config/tokens/FateZero.txt", "r")
bot.run(f.read())
f.close()
