"""
cogs.utility.buttonroles
~~~~~~~~~~~~~~~~~~~~~~~~~

A selfroles module using buttons instead of reactions

:copyright: (C) 2021-present Michael Stollings
:license: Proprietary and Confidential, see LICENSE for details
"""

from contextlib import suppress

from discord.ext import commands
from discord import ui, Interaction
import discord

from botutils import Conversation
from fate import Fate


allowed_mentions = discord.AllowedMentions(everyone=False, roles=True, users=False)


class ButtonRoles(commands.Cog):
    def __init__(self, bot: Fate):
        self.bot = bot
        self.menus = bot.utils.cache("button_roles")
        for key in self.menus.keys():
            self.menus.remove(key)
        self.global_cooldown = bot.utils.cooldown_manager(1, 3)
        if bot.is_ready():
            bot.loop.create_task(self.load_menus_on_start())

    @commands.Cog.listener("on_ready")
    async def load_menus_on_start(self):
        if not hasattr(self.bot, "menus_loaded"):
            self.bot.menus_loaded = False
        if not self.bot.menus_loaded:
            for guild_id, menus in self.menus.items():
                for msg_id, data in menus.items():
                    if data["style"] == "buttons":
                        self.bot.add_view(ButtonMenu(self, guild_id, msg_id))
                self.bot.menus_loaded = True

    @commands.group(name="role-menu", aliases=["rolemenu"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def role_menu(self, ctx: commands.Context):
        if not ctx.invoked_subcommand:
            e = discord.Embed(color=self.bot.config["theme_color"])
            e.set_author(name="Role Menus", icon_url=self.bot.user.avatar.url)
            if ctx.guild.icon:
                e.set_thumbnail(url=ctx.guild.icon.url)
            e.description = "Create menus for users to self assign roles via buttons\n**NOTE:** this feature is in beta"
            p: str = ctx.prefix
            e.add_field(
                name="◈ Usage",
                value=f"{p}role-menu create\n"
                      f"{p}~~role-menu set-message `msg_id` `new message`~~\n"
                      f"{p}~~role-menu add-role `msg_id` `@role`~~\n"
                      f"{p}~~role-menu remove-role `msg_id` `@role`~~\n"
                      f"{p}~~role-menu set-style `msg_id` `button/dropdown`~~"
            )
            count = 0
            if ctx.guild.id in self.menus:
                count = len(self.menus[ctx.guild.id])
            e.set_footer(text=f"{count} Active Menu")
            if count == 0 or count > 1:
                e.footer.text += "s"
            await ctx.send(embed=e)

    @commands.command(name="create")
    @commands.has_permissions(administrator=True)
    async def create_menu(self, ctx):
        convo = Conversation(ctx, delete_after=True)
        data = []
        await convo.send("reply with `done` when you're done adding roles")
        while True:
            reply = await convo.ask("What's a role name I should use")
            if reply.content.lower() == "done":
                break
            role = await self.bot.utils.get_role(ctx, reply.content)
            if not role:
                await convo.send("Role not found")
                continue
            data.append(role.id)
        reply = await convo.ask("#Mention the channel you want me to use")
        channel = reply.channel_mentions[0]
        msg = await channel.send("Choose your role")
        if ctx.guild.id not in self.menus:
            self.menus[ctx.guild.id] = {}
        self.menus[ctx.guild.id][str(msg.id)] = {
            "roles": data,
            "text": "Select your role",
            "style": "buttons",
        }
        view = ButtonMenu(cls=self, guild_id=ctx.guild.id, message_id=msg.id)
        await msg.edit(view=view)
        await self.menus.flush()

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        if payload.guild_id in self.menus:
            if str(payload.message_id) in self.menus[payload.guild_id]:
                await self.menus.remove_sub(payload.guild_id, payload.message_id)


class ButtonMenu(ui.View):
    def __init__(self, cls: ButtonRoles, guild_id: int, message_id: int):
        self.bot = cls.bot
        self.menus = cls.menus
        self.global_cooldown = cls.global_cooldown
        self.cooldown = cls.bot.utils.cooldown_manager(5, 25)
        self.guild_id = guild_id
        self.buttons = {}
        super().__init__(timeout=None)

        data = self.menus[guild_id][str(message_id)]
        guild = self.bot.get_guild(guild_id)
        for role_id in data["roles"]:
            role = guild.get_role(role_id)
            if not role:
                continue

            # Add a new button to the class
            button = ui.Button(
                label=role.name,
                style=discord.ButtonStyle.blurple,
                custom_id=f"{role_id}@{message_id}"
            )
            button.callback = self.surface_callback
            self.buttons[button.custom_id] = button
            self.add_item(button)

    async def surface_callback(self, interaction):
        """ Suppress exceptions in the actual callback function """
        with suppress(discord.errors.NotFound):
            await self.callback(interaction)

    async def callback(self, interaction: Interaction):
        """ The callback function for when a buttons pressed """
        async def remove_button(reason):
            """ Remove a button that can no longer be used """
            self.remove_item(self.buttons[custom_id])
            with suppress(KeyError):
                self.menus[self.guild_id][key]["roles"].remove(role_id)
            await self.menus.flush()
            await interaction.message.edit(view=self)
            return await interaction.response.send_message(reason, ephemeral=True)

        # Ensure the user isn't spamming buttons
        check1 = self.global_cooldown.check(interaction.user.id)
        check2 = self.cooldown.check(interaction.user.id)
        if check1 or check2:
            return await interaction.response.send_message(
                "You're on cooldown, try again in a moment", ephemeral=True
            )

        # Parse the key and get its relative data
        custom_id = interaction.data["custom_id"]
        key = custom_id.split("@")[1]
        role_id = int(custom_id.split("@")[0])

        # Fetch required variables
        guild = self.bot.get_guild(self.guild_id)
        member = guild.get_member(interaction.user.id)
        role = guild.get_role(role_id)
        name = self.buttons[custom_id].label

        if not guild or not member:
            return  # Cache isn't properly established
        if not role:
            return await remove_button(f"{name} doesn't seem to exist anymore")
        if role.position >= guild.me.top_role.position:
            return await remove_button(f"{name} is too high for me to manage")

        if role in member.roles:
            await member.remove_roles(role)
            action = "Removed"
        else:
            action = "Gave you"
            await member.add_roles(role)
        await interaction.response.send_message(
            f"{action} {role.mention}",
            ephemeral=True
        )


def setup(bot: Fate):
    bot.add_cog(ButtonRoles(bot))
