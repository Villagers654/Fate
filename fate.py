import json
import traceback
from time import time
from datetime import datetime
import os
import asyncio
import logging

from discord.ext import commands
import discord
import aiomysql
from pymysql.err import OperationalError
from termcolor import cprint

from utils import outh, utils, tasks, colors


class Fate(commands.AutoShardedBot):
    def __init__(self, **options):
        with open('./data/config.json', 'r') as f:
            self.config = json.load(f)  # type: dict
        self.debug_mode = self.config['debug_mode']
        self.pool = None                # MySQL Pool initialized on_ready
        self.login_errors = []          # Exceptions ignored during startup
        self.logs = []                  # Logs to send to discord, empties out quickly

        self.initial_extensions = [     # Cogs to load before logging in
            'error_handler', 'config', 'menus', 'core', 'music', 'mod', 'welcome', 'farewell', 'notes', 'archive',
            'coffeeshop', 'custom', 'actions', 'reactions', 'responses', 'textart', 'fun', 'dev', '4b4t', 'readme',
            'reload', 'embeds', 'polis', 'apis', 'chatbridges', 'clean_rythm', 'utility', 'psutil', 'rules',
            'duel_chat', 'selfroles', 'lock', 'audit', 'cookies', 'backup', 'stats', 'server_list', 'emojis',
            'logger', 'autorole', 'changelog', 'restore_roles', 'chatbot', 'anti_spam', 'anti_raid', 'chatfilter',
            'nsfw', 'minecraft', 'chatlock', 'rainbow', 'system', 'user', 'limiter', 'dm_channel', 'factions',
            'secure_overwrites', 'server_setup', 'secure-log', 'global-chat', 'beta', 'ranking'
        ]
        self.awaited_extensions = []    # Cogs to load when the internal cache is ready

        self.utils = utils              # Custom utility functions
        self.result = utils.Result      # Custom Result Object Creator
        self.memory = utils.MemoryInfo  # Class for easily accessing memory usage
        self.tasks = tasks.Tasks(self)  # Task Manager

        # deprecated shit
        self.get_stats = utils.get_stats()
        self.get_config = utils.get_config()

        super().__init__(
            command_prefix=utils.get_prefixes,
            activity=discord.Game(name=self.config['startup_status']), **options
        )

    async def create_pool(self):
        sql = outh.MySQL()
        try:
            self.pool = await aiomysql.create_pool(
                host=sql.host,
                port=sql.port,
                user=sql.user,
                password=sql.password,
                db=sql.db,
                loop=self.loop,
                minsize=10,
                maxsize=64
            )
        except (ConnectionRefusedError, OperationalError):
            self.log("Couldn't connect to SQL server", 'CRITICAL', tb=traceback.format_exc())
            self.unload(*self.initial_extensions, log=False)
            self.log("Logging out..")
            await self.logout()
        else:
            self.log(f"Initialized db {sql.db} with {sql.user}@{sql.host}")

    async def insert(self, table, *values):
        while not self.pool:
            await asyncio.sleep(0.21)
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                command = f"INSERT INTO {table} VALUES ({', '.join([str(v) for v in values])});"
                await cur.execute(command)
                await conn.commit()

    async def select(self, sql, all=False):
        while not self.pool:
            await asyncio.sleep(0.21)
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(f"SELECT "+sql if not str(sql).lower().startswith('select') else sql)
                if all:
                    return await cur.fetchall()
                return await cur.fetchone()

    async def update(self, table, **where):
        while not self.pool:
            await asyncio.sleep(0.21)
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                set_key, set_value = list(where.items())[0]
                command = f"UPDATE {table} SET {set_key} = {set_value}"
                for i, (key, value) in enumerate(where.items()):
                    if i == 0:
                        continue
                    if i == 1:
                        command += f" WHERE {key} = {value}"
                    else:
                        command += f" and {key} = {value}"
                await cur.execute(command+';')
                await conn.commit()

    def load(self, *extensions):
        for cog in extensions:
            try:
                self.load_extension(f"cogs.{cog}")
                self.log(f"Loaded {cog}")
            except commands.ExtensionNotFound:
                self.log(f"Couldn't find {cog}")
            except commands.ExtensionError:
                self.log(f"Couldn't load {cog}", tb=traceback.format_exc())

    def unload(self, *extensions, log=True):
        for cog in extensions:
            try:
                self.unload_extension(f"cogs.{cog}")
                if log:
                    self.log(f"Unloaded {cog}")
            except commands.ExtensionNotLoaded:
                if log:
                    self.log(f"Failed to unload {cog}")

    def reload(self, *extensions):
        for cog in extensions:
            try:
                self.reload_extension(f"cogs.{cog}")
                self.log(f"Reloaded {cog}")
            except commands.ExtensionNotFound:
                self.log(f"Reloaded {cog}")
            except commands.ExtensionNotLoaded:
                self.log(f"{cog} isn't loaded")
            except commands.ExtensionError:
                self.log(f"Ignoring exception in Cog: {cog}", tb=traceback.format_exc())

    def log(self, message, level='INFO', tb=None, color=None):
        if level == 'DEBUG' and not self.debug_mode:
            return
        now = str(datetime.now().strftime("%I:%M%p"))
        if now.startswith('0'):
            now = now.replace('0', '', 1)
        lines = []
        for line in message.split('\n'):
            msg = f"{now} | {level} | {line}"
            if level == 'DEBUG' and self.config['debug_mode']:
                cprint(msg, color if color else 'cyan')
            elif level == 'INFO':
                cprint(msg, color if color else 'green')
            elif level == 'CRITICAL':
                cprint(msg, color if color else 'red')
            lines.append(msg)
        if tb:
            cprint(str(tb), color if color else 'red')
            lines.append(str(tb))
        self.logs.append('\n'.join(lines))
        self.logs = self.logs[:1000]

    def run(self):
        if bot.initial_extensions:
            self.log("Loading initial cogs", color='yellow')
            self.load(*self.initial_extensions)
            self.log("Finished loading initial cogs\nLogging in..", color='yellow')
        super().run(outh.tokens('fatezero'))


start_time = time()
bot = Fate(max_messages=16000)
bot.remove_command('help')

# debug_task log
if os.path.isfile('discord.log'):  # reset the file on startup so the debug_log task doesn't resend logs
    os.remove('discord.log')       # also keeps the file size down and speeds things up
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


@bot.event
async def on_shard_ready(shard_id):
    bot.log(f"Shard {shard_id} connected")


@bot.event
async def on_ready():
    bot.log(
        '------------'
        '\nLogged in as'
        f'\n{bot.user}'
        f'\n{bot.user.id}'
        '\n------------',
        color='yellow'
    )
    await bot.create_pool()
    if bot.awaited_extensions:
        bot.log("Loading awaited cogs", color='yellow')
        bot.load(*bot.awaited_extensions)
        bot.log("Finished loading awaited cogs", color='yellow')
    bot.tasks.ensure_all()
    seconds = round(time() - start_time)
    bot.log(f"Startup took {seconds} seconds")
    for error in bot.login_errors:
        bot.log("Error ignored during startup", level='CRITICAL', tb=error)


@bot.event
async def on_message(msg):
    if '@everyone' in msg.content or '@here' in msg.content:
        msg.content = msg.content.replace('@', '!')
    blacklist = [
        'trap', 'dan', 'gel', 'yaoi'
    ]
    if '--dm' in msg.content and not any(x in msg.content for x in blacklist):
        msg.content = msg.content.replace(' --dm', '')
        channel = await msg.author.create_dm()
        msg.channel = channel
    if msg.guild and not msg.channel.permissions_for(msg.guild.me).send_messages:
        return
    await bot.process_commands(msg)


@bot.event
async def on_guild_join(guild):
    channel = bot.get_channel(bot.config['log_channel'])
    e = discord.Embed(color=colors.pink())
    e.set_author(name="Bot Added to Guild", icon_url=bot.user.avatar_url)
    if guild.icon_url:
        e.set_thumbnail(url=guild.icon_url)
    e.description = f"**Name:** {guild.name}\n" \
                    f"**ID:** {guild.id}\n" \
                    f"**Owner:** {guild.owner}\n" \
                    f"**Members:** [`{len(guild.members)}`]"
    await channel.send(embed=e)
    conf = bot.utils.get_config()  # type: dict
    if guild.owner.id in conf['blocked']:
        await guild.leave()


@bot.event
async def on_guild_remove(guild: discord.Guild):
    channel = bot.get_channel(bot.config['log_channel'])
    e = discord.Embed(color=colors.pink())
    e.set_author(name="Bot Left or Was Removed", icon_url=bot.user.avatar_url)
    if guild.icon_url:
        e.set_thumbnail(url=guild.icon_url)
    e.description = f"**Name:** {guild.name}\n" \
                    f"**ID:** {guild.id}\n" \
                    f"**Owner:** {guild.owner}\n" \
                    f"**Members:** [`{len(guild.members)}`]"
    with open('members.txt', 'w') as f:
        f.write('\n'.join([f'{m.id}, {m}, {m.mention}' for m in guild.members]))
    await channel.send(embed=e, file=discord.File('members.txt'))
    os.remove('members.txt')


@bot.event
async def on_command(_ctx):
    stats = bot.utils.get_stats()  # type: dict
    stats['commands'].append(str(datetime.now()))
    with open('./data/stats.json', 'w') as f:
        json.dump(stats, f, ensure_ascii=False)


bot.log("Starting Bot", color='yellow')
bot.start_time = datetime.now()
try:
    bot.run()
except discord.errors.LoginFailure:
    print("Invalid Token")
except asyncio.exceptions.CancelledError:
    pass
