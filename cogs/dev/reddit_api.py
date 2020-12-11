import asyncio
import traceback
from time import time


from discord.ext import commands, tasks
import discord
import asyncpraw

from utils import colors, auth


class Reddit(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.enabled = []
        if "reddit" not in self.bot.tasks:
            self.bot.tasks["reddit"] = {}
        for guild_id, task in list(self.bot.tasks["reddit"].items()):
            task.cancel()
            del self.bot.tasks["reddit"][guild_id]
        self.ensure_subscriptions_task.start()

    def cog_unload(self):
        self.ensure_subscriptions_task.cancel()
        for guild_id, task in list(self.bot.tasks["reddit"].items()):
            task.cancel()

    @tasks.loop(minutes=1)
    async def ensure_subscriptions_task(self):
        await asyncio.sleep(0.21)
        if not self.bot.is_ready() or not self.bot.pool:
            return
        if "reddit" not in self.bot.tasks:
            self.bot.tasks["reddit"] = {}
        if not self.enabled:
            async with self.bot.cursor() as cur:
                await cur.execute("select guild_id from reddit;")
                results = await cur.fetchall()
            self.enabled = [result[0] for result in results]
        for guild_id in self.enabled:
            if guild_id not in self.bot.tasks["reddit"] or self.bot.tasks["reddit"][guild_id].done():
                self.bot.tasks["reddit"][guild_id] = self.bot.loop.create_task(
                    self.handle_subscription(guild_id)
                )
        for guild_id, task in self.bot.tasks["reddit"].items():
            if guild_id not in self.enabled:
                task.cancel()
        await asyncio.sleep(60)

    async def handle_subscription(self, guild_id):
        async with self.bot.cursor() as cur:
            await cur.execute(
                f"select channel_id, subreddit, new_posts, text, images, rate "
                f"from reddit "
                f"where guild_id = {guild_id} "
                f"limit 1;"
            )
            results = await cur.fetchall()
        if not results:
            return

        channel_id, subreddit_name, new_posts, text, images, rate = results[0]
        exts = ["png", "jpg", "jpeg", "gif"]
        cache = []
        async with self.bot.cursor() as cur:
            await cur.execute(
                f"select post_id from reddit_cache "
                f"where guild_id = {guild_id};"
            )
            results = await cur.fetchall()
        for result in results:
            cache.append(result[0])

        channel = self.bot.get_channel(channel_id)
        await channel.send("Subscription task was started")
        get_description = lambda post: post.selftext if post.selftext else post.title
        creds = auth.Reddit()
        client = asyncpraw.Reddit(
            client_id=creds.client_id,
            client_secret=creds.client_secret,
            user_agent=creds.user_agent,
        )
        subreddit_name = subreddit_name.replace(" ", "")
        reddit = await client.subreddit(subreddit_name.replace(",", "+"))
        subreddit = reddit.new if new_posts else reddit.hot
        search_limit = 25

        while True:
            await asyncio.sleep(0.21)
            posts = []
            try:
                async for post in subreddit(limit=search_limit):
                    if post.stickied or post.id in cache:
                        continue
                    has_images = any(post.url.endswith(ext) for ext in exts)
                    if images and any(post.url.endswith(ext) for ext in exts):
                        posts.append(post)
                    elif text and not images and not has_images:
                        posts.append(post)
                    elif text and (post.title or post.selftext):
                        posts.append(post)
                    if len(posts) == 50:
                        break

                if not posts:
                    if search_limit == 250:
                        await channel.send(f"No results after searching r/{subreddit_name}")
                        await asyncio.sleep(rate)
                        continue
                    search_limit += 25
                    continue

                for post in posts:
                    url = f"https://reddit.com{post.permalink}"
                    await asyncio.sleep(rate)
                    await post.author.load()
                    await post.subreddit.load()

                    e = discord.Embed(color=colors.red())
                    icon_img = self.bot.user.avatar_url
                    if hasattr(post.author, "icon_img"):
                        icon_img = post.author.icon_img
                    e.set_author(name=f"u/{post.author.name}", icon_url=icon_img, url=post.url)

                    # Set to use text
                    if text and (post.title or post.selftext):
                        enum = enumerate(self.bot.utils.split(get_description(post), 914))
                        for i, chunk in enum:
                            if i == 0:
                                e.description = chunk
                            elif i == 1:
                                e.description += chunk
                            elif i == 5:
                                e.add_field(
                                    name="Reached the character limit",
                                    value=f"Click the [hyperlink]({url}) to view more",
                                    inline=False
                                )
                                break
                            else:
                                e.add_field(
                                    name="Additional Text",
                                    value=chunk,
                                    inline=False
                                )

                    # Set to use images
                    if images and "." in post.url.split("/")[post.url.count("/")]:
                        if any(post.url.endswith(ext) for ext in exts):
                            e.set_image(url=post.url)
                        else:
                            e.description += f"\n[click to view attachment]({post.url})"

                    e.set_footer(
                        text=f"r/{post.subreddit.display_name} | "
                             f"⬆ {post.score} | "
                             f"👍 {str(post.upvote_ratio).lstrip('0.')}% | "
                             f"💬 {post.num_comments}"
                    )
                    await channel.send(embed=e)
                    async with self.bot.cursor() as cur:
                        await cur.execute(
                            f"insert into reddit_cache values ({guild_id}, '{post.id}', {time()});"
                        )
                    cache.append(post.id)
            except asyncio.CancelledError:
                return await channel.send("Subscription task was cancelled")
            except:
                await channel.send(traceback.format_exc())
                await asyncio.sleep(1.21)
                continue

    @commands.group(name="reddit", aliases=["reddit-api"])
    async def _reddit(self, ctx):
        if not ctx.invoked_subcommand:
            pass
        elif not ctx.invoked_subcommand:
            e = discord.Embed(color=colors.fate())
            e.set_author(name="Reddit", icon_url=ctx.author.avatar_url)
            e.description = "Pulls from a subreddits posts and can subscribe to a " \
                            "designated TextChannel. Can be sorted by top or new and can collect " \
                            "images only, text only, or title only depending on preference"

    @_reddit.command(name="subscribe")
    @commands.has_permissions(administrator=True)
    async def _subscribe(self, ctx, *, subreddit):
        subreddit = subreddit.lstrip("r/")
        await ctx.send("Do you want the bot to send Hot, or New posts")
        async with self.bot.require("message", ctx, handle_timeout=True) as msg:
            if "hot" not in msg.content.lower() and "new" not in msg.content.lower():
                return await ctx.send("That wasn't a valid response")
            if "hot" in msg.content.lower():
                new = False
            else:
                new = True

        await ctx.send("Should I send Images, Text, or Both")
        async with self.bot.require("message", ctx, handle_timeout=True) as msg:
            content = msg.content.lower()
            if "images" not in content and "text" not in content and "both" not in content:
                return await ctx.send("Invalid response")
            images = text = False
            if "images" in msg.content.lower():
                images = True
            elif "text" in msg.content.lower():
                text = True
            elif "both" in msg.content.lower():
                images = text = True

        await ctx.send(
            "At what rate (in seconds) should I send a reddit post. "
            "You can pick between 5 minutes to 24 hours"
        )
        async with self.bot.require("message", ctx, handle_timeout=True) as msg:
            if not msg.content.isdigit():
                return await ctx.send("Bruh.. a number please\nRedo the command")
            rate = int(msg.content)
        if rate < 60 * 5 and ctx.author.id not in self.bot.owner_ids:
            return await ctx.send("That rates too fast\nRedo the command")
        if rate > 60 * 60 * 24:
            return await ctx.send("That rates too...... long.......for............me.....owo blushes")
            # i looked away for literally 20 seconds. and you do this
            # without regerts

        guild_id = ctx.guild.id
        async with self.bot.cursor() as cur:
            await cur.execute(
                f"insert into reddit "
                f"values ({guild_id}, {ctx.channel.id}, '{subreddit}', {new}, {text}, {images}, {rate}) "
                
                f"on duplicate key "
                f"update "
                f"guild_id = {guild_id}, "
                f"channel_id = {ctx.channel.id}, "
                f"subreddit = '{subreddit}', "
                f"new_posts = {new}, "
                f"text = {text}, "
                f"images = {images}, "
                f"rate = {rate};"
            )
        self.enabled.append(guild_id)
        if ctx.guild.id in self.bot.tasks["reddit"]:
            self.bot.tasks["reddit"][ctx.guild.id].cancel()
            await ctx.send("Cancelled existing task")
        self.bot.tasks["reddit"][ctx.guild.id] = self.bot.loop.create_task(
            self.handle_subscription(guild_id)
        )

        await ctx.send(
            f"Set up the subreddit subscription. You'll now receive "
            f"a new post every {self.bot.utils.get_time(rate)}"
        )

    @_reddit.command(name="disable")
    @commands.has_permissions(administrator=True)
    async def disable(self, ctx):
        if ctx.guild.id not in self.enabled:
            return await ctx.send("This server currently isn't subscribed to a subreddit")
        async with self.bot.cursor() as cur:
            await cur.execute(f"delete from reddit where guild_id = {ctx.guild.id};")
        self.enabled.remove(ctx.guild.id)
        if ctx.guild.id in self.bot.tasks["reddit"]:
            self.bot.tasks["reddit"][ctx.guild.id].cancel()
            del self.bot.tasks["reddit"][ctx.guild.id]
        await ctx.send("Disabled the reddit subscription")


def setup(bot):
    bot.add_cog(Reddit(bot))
