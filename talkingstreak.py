import discord, time, math, asyncio
from discord.ext import commands
from discord.ui import Button, View
import datastore, shared

MAX_TEXT_LENGTH = 1024

bot: discord.Bot = shared.bot

def get_d_roles(data, user: discord.Member, streak):
    toadd = set()
    toremove = set()
    message = None
    roles = {i.id for i in user.roles}
    if streak == 0 or data["talkstreak"]["settings"]["stack_roles"]:
        for i, v in data["talkstreak"]["roles"].items():
            if v["days"] <= streak and not int(i) in roles:
                toadd.add(int(i))
                message = v["message_on_get"] if "message_on_get" in v else None
            else:
                message = None
                if v["days"] > streak and not data["talkstreak"]["settings"]["save_roles"]:
                    toremove.add(int(i))
    else:
        cur = None
        for i, v in data["talkstreak"]["roles"].items():
            if v["days"] <= streak:
                if cur is None or cur[1] <= v["days"]:
                    if cur is not None:
                        toremove.add(cur[0])
                    cur = (int(i), v["days"])
                    if not int(i) in roles:
                        message = v["message_on_get"] if "message_on_get" in v else None
            elif not data["talkstreak"]["settings"]["save_roles"]:
                toremove.add(int(i))
        if not cur[0] in roles:
            toadd.add(cur[0])
    return toadd, toremove, message

async def edit_roles(data, user: discord.Member, streak, guild: discord.Guild):
    toadd, toremove, message = get_d_roles(data, user, streak)
    if len(toremove) > 0:
        for i in toremove:
            try:
                if guild.get_role(i):
                    await user.remove_roles(discord.Object(id=i), reason="Removing all roles that are lower than user's streak role.")
            except discord.Forbidden:
                print(f"I tried removing the {user.display_name}'s {guild.get_role(i).name} role, but I couldn't do it. Try giving me Manage Roles permission or moving my role above the role.")
            except discord.HTTPException:
                print(f"I tried removing the {user.display_name}'s {guild.get_role(i).name} role, but I couldn't do it because of something on Discord's side. Try some time later!")
    if len(toadd) > 0:
        for i in toadd:
            try:
                if guild.get_role(i):
                    await user.add_roles(discord.Object(id=i), reason="Adding member's streak roles.")
            except discord.Forbidden:
                print(f"I tried adding the {guild.get_role(i).name} role to {user.display_name}, but I couldn't do it. Try giving me Manage Roles permission or moving my role above the role.")
            except:
                print(f"I tried adding the {guild.get_role(i).name} role to {user.display_name}, but I couldn't do it because of something on Discord's side. Try some time later!")
    
        message = message or data["talkstreak"]["default_message"]
        usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
        embed = discord.Embed(colour = usedcolor, title="New roles!", description=message)
        return embed, i
    return [None, None]

async def edit_name(user: discord.Member, streak):
    name = user.display_name
    i = len(name) - 1
    if not name.find("🔥") or not name[i].isdigit():
        if len(name) + len(f" 🔥{streak}") <= 32:
            name = name+f" 🔥{streak}"
    else:
        while name[i] != "🔥":
            i -= 1
        name = (name[:i]+f" 🔥{streak}")[:32]
    try:
        await user.edit(nick=name)
    except discord.Forbidden:
        print(f"I tried changing the {user.display_name}'s nickname, but I couldn't do it. Try giving me Manage Nicknames permission or moving my role up. I also can't edit owner's nickname!")
    except discord.HTTPException:
        print(f"I tried changing the {user.display_name}'s nickname, but I couldn't do it because of something on Discord's side. Try some time later!")

async def remove_name(user: discord.Member):
    name = user.display_name
    i = len(name) - 1
    if not name.find("🔥") or not name[i].isdigit():
        return
    else:
        while name[i] != "🔥":
            i -= 1
        name = (name[:i])[:32]
    try:
        await user.edit(nick=name)
    except discord.Forbidden:
        print(f"I tried changing the {user.display_name}'s nickname, but I couldn't do it. Try giving me Manage Nicknames permission or moving my role up. I also can't edit owner's nickname!")
    except discord.HTTPException:
        print(f"I tried changing the {user.display_name}'s nickname, but I couldn't do it because of something on Discord's side. Try some time later!")

async def message_func(message: discord.Message, data, bot: discord.Bot):
    id = str(message.author.id)
    if not id in data["talkstreak"]["cd_check"] or data["talkstreak"]["cd_check"][id] + data["talkstreak"]["cooldown"] < time.time():
        if str(message.channel.id) in data["talkstreak"]["banned_channels"]:
            return
        user = await bot.fetch_user(int(id))
        member = await message.guild.fetch_member(user.id)
        if not id in data["talkstreak"]["streaks"]:
            data["talkstreak"]["streaks"][id] = 1
        else:
            data["talkstreak"]["streaks"][id] += 1
            if data["talkstreak"]["streaks"][id] >= data["talkstreak"]["min_show_streak"] and datastore.datastore.getsetting(int(id), "display_streak"):
                await edit_name(member, data["talkstreak"]["streaks"][id])
            else:
                await remove_name(member)
        data["talkstreak"]["cd_check"][id] = math.ceil(time.time())
        msg, role = await edit_roles(data, member, data["talkstreak"]["streaks"][id], message.channel.guild)
        if msg:
            channel_id = data["talkstreak"]["channel"] or message.channel.id
            if channel_id != 0:
                msg.description = msg.description.replace("{user}", f"<@{id}>").replace("{days}", str(data["talkstreak"]["streaks"][id]))
                if channel_id == 1:
                    msg.description = msg.description.replace("{role}", f'**@{message.channel.guild.get_role(role).name}**')
                    try:
                        await user.send(embed=msg)
                    except discord.Forbidden:
                        print(f"I tried sending a DM to {user.name}, but I couldn't do it. Try giving me the required permissions.")
                    except:
                        print(f"I tried sending a DM to {user.name}, but I couldn't do it. Try giving me the required permissions.")
                else:
                    msg.description = msg.description.replace("{role}", f'<@&{message.channel.guild.get_role(role).id}>')
                    if channel_id == 2:
                        channel_id = message.channel.id
                    channel = bot.get_channel(channel_id)
                    if not channel:
                        channel = bot.get_channel(message.channel.id)
                    try:
                        await channel.send(content=data["talkstreak"]["settings"]["ping_member"] and f"<@{id}>" or None, embed=msg)
                    except discord.Forbidden:
                        print(f"I tried sending a message to #{channel.name}, but I couldn't do it. Try giving me Send Messages permission, or blacklist the channel.")
                    except:
                        print(f"I tried sending a message to #{channel.name}, but I couldn't do it because of something on Discord's side. Try some time later!")
    
        await hang_a_rifle(data, id)

# -- TIMER FOR LOSING STREAK

async def losestreak(data, id):
    if not data["modulesenabled"]["talkstreak"]:
        return
    streak = 0
    guild: discord.Guild = bot.get_guild(data["guild_id"])
    member = await guild.fetch_member(int(id))
    if not data["talkstreak"]["settings"]["save_roles"]:
        await edit_roles(data, member, 0, guild)
    if id in data["talkstreak"]["cd_check"]:
        del data["talkstreak"]["cd_check"][id]
    if id in data["talkstreak"]["streaks"]:
        streak = data["talkstreak"]["streaks"][id]
        del data["talkstreak"]["streaks"][id]
    await remove_name(member)
    if streak >= max(2, data["talkstreak"]["min_show_streak"]) and datastore.datastore.getsetting(int(id), "dm_streak_loss"):
        message = data["talkstreak"]["loss_message"]
        message = message.replace("{user}", f'<@{id}>').replace("{days}", str(streak)).replace("{guild}", guild.name)
        usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
        embed = discord.Embed(colour = usedcolor, title="Streak lost", description=message, footer=discord.EmbedFooter("If you want to disable these notifications, use /settings self."))
        user = await bot.fetch_user(int(id))
        await user.send(embed=embed)

async def rifle(data, id):
    try:
        id = str(id)
        if not id in data["talkstreak"]["cd_check"]:
            return
        timetowait = data["talkstreak"]["cd_check"][id]-time.time()+data["talkstreak"]["fail_time"]+data["talkstreak"]["cooldown"]
        if timetowait > 0:
            rememberedtime = data["talkstreak"]["cd_check"][id]
            await asyncio.sleep(timetowait)
            cd_check = data["talkstreak"]["cd_check"][id]
            if rememberedtime == cd_check:
                await losestreak(data, id)
            else:
                print("Attempted to skin a member alive, but cd_check was changed beforehand.")
                if cd_check > rememberedtime:
                    await hang_a_rifle(data, id)
        else:
            await losestreak(data, id)
    except asyncio.CancelledError:
        pass

hanged_loss = dict()
async def hang_a_rifle(data, id):
    if id in hanged_loss:
        hanged_loss[id].cancel()
    task = asyncio.create_task(rifle(data, id))
    hanged_loss[id] = task

async def professional_rifle_hanger(data):
    if not data["modulesenabled"]["talkstreak"]:
        return
    for i in data["talkstreak"]["cd_check"].keys():
        await hang_a_rifle(data, i)

talkedit = discord.SlashCommandGroup("streak", "Commands to manage talking streak.")
talkset = talkedit.create_subgroup("set", "Edits talking streak parameters.")
talkadd = talkedit.create_subgroup("add", "Adds some talking streak parameters.")
talkremove = talkedit.create_subgroup("remove", "Removes some talking streak parameters.")
roleset = talkedit.create_subgroup("role", "Commands to add or remove role rewards.")

# -- FUNCTIONS --

def gr():
    async def getroles(ctx: discord.AutocompleteContext):
        data = datastore.datastore.getdata(ctx.interaction.guild_id)
        values = []
        for i, v in data["talkstreak"]["roles"].items():
            role: discord.Role = ctx.interaction.guild.get_role(int(i))
            if role is not None:
                values.append(discord.OptionChoice(name=f"{role.name} -- ({str(v['days'])}🔥 days)", value=i))
        return [c for c in values if ctx.value.lower() in c.name.lower()][:25]
    return getroles
get_roles = gr()

def gc(d):
    async def getchannel(ctx: discord.AutocompleteContext):
        if not d:
            values = [discord.OptionChoice(name=f"Don't send messages", value="0"), discord.OptionChoice(name=f"Same channel as the user", value="2"), discord.OptionChoice(name=f"User's DMs", value="1")]
        else:
            values = []
        for i in await ctx.interaction.guild.fetch_channels():
            issue = ""
            perms = i.permissions_for(ctx.interaction.guild.me)
            if not perms.send_messages and not d:
                issue = "-- Bot lacks permissions to send messages here"
            values.append(discord.OptionChoice(name=f"#{i.name} {issue}", value=str(i.id)))
        return [c for c in values if ctx.value.lower() in c.name.lower()][:25]
    return getchannel
get_channel = gc(False)
get_channel_no_warn = gc(True)

async def check_eligibility(ctx: discord.Interaction, data):
    if ctx.user.id in data["talkstreak"]["trusted"]["members"] or ctx.channel.permissions_for(ctx.user).manage_guild or {i.id for i in ctx.user.roles} & {int(i) for i in data["talkstreak"]["trusted"]["roles"].keys()}:
        return True
    else:
        embed = discord.Embed(colour = discord.Colour.red(), title="Error", description="You don't have the permissions and you're not in trusted member list to use this command!")
        message = await ctx.response.send_message(embed=embed, ephemeral=True)
        return False


# -- TRUSTED MEMBERS --

@talkedit.command(name="add_member", description="Adds a trusted member to manage talking streak.")
@discord.option(name="member", type=discord.SlashCommandOptionType.user, description="Member to add to trusted list.")
async def addmember(ctx: discord.Interaction, member):
    data = datastore.datastore.getdata(ctx.guild_id)
    if ctx.channel.permissions_for(ctx.user).manage_guild:
        uniqueid = str(member.id)
        if uniqueid in data["talkstreak"]["trusted"]["members"]:
            embed = discord.Embed(colour = discord.Colour.red(), title="Error", description=f"**@{member.name}** is already in trusted member list, so they were not added.", thumbnail=member.avatar.url)
            message = await ctx.response.send_message(embed=embed, ephemeral=True)
        else:
            data["talkstreak"]["trusted"]["members"][uniqueid] = True
            usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
            embed = discord.Embed(colour = usedcolor, title="Added member", description=f"Added **@{member.name}** to trusted member list.", thumbnail=member.avatar.url)
            message = await ctx.response.send_message(embed=embed, ephemeral=True)
    else:
        embed = discord.Embed(colour = discord.Colour.red(), title="Error", description="You don't have the permissions to use this command!")
        message = await ctx.response.send_message(embed=embed, ephemeral=True)
        return False
            
@talkedit.command(name="remove_member", description="Removes a trusted member from managing talking streak.")
@discord.option(name="member", type=discord.SlashCommandOptionType.user, description="Member to remove from trusted list.")
async def removemember(ctx: discord.Interaction, member):
    data = datastore.datastore.getdata(ctx.guild_id)
    if ctx.channel.permissions_for(ctx.user).manage_guild:
        uniqueid = str(member.id)
        if not uniqueid in data["talkstreak"]["trusted"]["members"]:
            embed = discord.Embed(colour = discord.Colour.red(), title="Error", description=f"**@{member.name}** is not in trusted member list.", thumbnail=member.avatar.url)
            message = await ctx.response.send_message(embed=embed, ephemeral=True)
        else:
            del data["talkstreak"]["trusted"]["members"][uniqueid]
            usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
            embed = discord.Embed(colour = usedcolor, title="Removed member", description=f"Removed **@{member.name}** from trusted member list.", thumbnail=member.avatar.url)
            message = await ctx.response.send_message(embed=embed, ephemeral=True)
    else:
        embed = discord.Embed(colour = discord.Colour.red(), title="Error", description="You don't have the permissions to use this command!")
        message = await ctx.response.send_message(embed=embed, ephemeral=True)
        return False


@talkedit.command(name="add_role", description="Adds a trusted role to manage talking streak.")
@discord.option(name="role", type=discord.SlashCommandOptionType.role, description="Role to add to trusted list.")
async def addrole(ctx: discord.Interaction, role):
    data = datastore.datastore.getdata(ctx.guild_id)
    if ctx.channel.permissions_for(ctx.user).manage_guild:
        uniqueid = str(role.id)
        if uniqueid in data["talkstreak"]["trusted"]["roles"]:
            embed = discord.Embed(colour = discord.Colour.red(), title="Error", description=f"**<@{role.name}>** is already in trusted roles list, so it was not added.")
            message = await ctx.response.send_message(embed=embed, ephemeral=True)
        else:
            data["talkstreak"]["trusted"]["roles"][uniqueid] = True
            usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
            embed = discord.Embed(colour = usedcolor, title="Added role", description=f"Added **<@{role.name}>** to trusted role list.")
            message = await ctx.response.send_message(embed=embed, ephemeral=True)
    else:
        embed = discord.Embed(colour = discord.Colour.red(), title="Error", description="You don't have the permissions to use this command!")
        message = await ctx.response.send_message(embed=embed, ephemeral=True)
        return False
            
@talkedit.command(name="remove_role", description="Removes a trusted role from managing talking streak.")
@discord.option(name="role", type=discord.SlashCommandOptionType.role, description="role to remove from trusted list.")
async def removerole(ctx: discord.Interaction, role):
    data = datastore.datastore.getdata(ctx.guild_id)
    if ctx.channel.permissions_for(ctx.user).manage_guild:
        uniqueid = str(role.id)
        if not uniqueid in data["talkstreak"]["trusted"]["roles"]:
            embed = discord.Embed(colour = discord.Colour.red(), title="Error", description=f"**<@{role.name}>** is not in trusted roles list.")
            message = await ctx.response.send_message(embed=embed, ephemeral=True)
        else:
            del data["talkstreak"]["trusted"]["roles"][uniqueid]
            usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
            embed = discord.Embed(colour = usedcolor, title="Removed role", description=f"Removed **<@{role.name}>** from trusted roles list.")
            message = await ctx.response.send_message(embed=embed, ephemeral=True)
    else:
        embed = discord.Embed(colour = discord.Colour.red(), title="Error", description="You don't have the permissions to use this command!")
        message = await ctx.response.send_message(embed=embed, ephemeral=True)
        return False

# -- SETTINGS --

@talkset.command(name="channel", description="Sets a channel where role obtainment messages will be posted.")
@discord.option(name="channel", autocomplete=get_channel, description="Channel where messages will be sent.")
async def set_channel(ctx: discord.Interaction, channel):
    data = datastore.datastore.getdata(ctx.guild_id)
    if await check_eligibility(ctx, data):
        channel = int(channel)
        data["talkstreak"]["channel"] = int(channel)
        usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
        desc = {2: "Messages will now be sent to the same channel as where user has messaged (if possible)", 1: "Messages will now be sent to user's DMs", 
                0: "Messages will not be sent to any of the channels."}
        if channel in desc:
            desc = channel
        else:
            desc = f"Messages will now be sent to **<#{channel}>**."
        embed = discord.Embed(colour = usedcolor, title=f'Channel for role award messages changed', description=desc)
        message = await ctx.response.send_message(embed=embed, ephemeral=True)

@talkset.command(name="cooldown", description="Changes time between two day counts for a streak.")
@discord.option(name="time", type=int, description="New cooldown time, in seconds (Default: 72000 seconds/20 hours).")
async def cd_change(ctx: discord.Interaction, time):
    data = datastore.datastore.getdata(ctx.guild_id)
    if await check_eligibility(ctx, data):
        data["talkstreak"]["cooldown"] = max(time, 5)
        usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
        embed = discord.Embed(colour = usedcolor, title=f'Streak cooldown changed', description=f"Streak cooldown changed to {time} seconds.")
        message = await ctx.response.send_message(embed=embed, ephemeral=True)

@talkset.command(name="fail_time", description="Changes time until a streak will be lost, minus the cooldown time.")
@discord.option(name="time", type=int, description="New time until a streak loss, in seconds (Default: 100800 seconds/28 hours).")
async def ft_change(ctx: discord.Interaction, time):
    data = datastore.datastore.getdata(ctx.guild_id)
    if await check_eligibility(ctx, data):
        data["talkstreak"]["fail_time"] = max(time, 5)
        usedcolor = discord.Color.from_rgb(*data["misc"]["color"])

        await professional_rifle_hanger(data)

        embed = discord.Embed(colour = usedcolor, title=f'Time until a streak loss changed', description=f"Time until a streak loss changed to {time} seconds.")
        message = await ctx.response.send_message(embed=embed, ephemeral=True)

@talkset.command(name="award_text", description="Changes a text for a role obtainment, if a role doesn't have a custom text.")
@discord.option(name="text", type=str, description="Custom award text. Use {user} for member name, {days} for user streak and {role} for role obtained.")
async def change_text(ctx: discord.Interaction, text):
    data = datastore.datastore.getdata(ctx.guild_id)
    if await check_eligibility(ctx, data):
        data["talkstreak"]["roles"]["default_message"] = text[:MAX_TEXT_LENGTH]
        usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
        embed = discord.Embed(colour = usedcolor, title=f'Changed obtainment text', description=f"Changed text for a default role obtainment:\n{text}")
        message = await ctx.response.send_message(embed=embed, ephemeral=True)

@talkset.command(name="streak_loss_text", description="Changes a text for a streak loss sent to user's DMs, unless they have that disabled.")
@discord.option(name="text", type=str, description="Custom award text. Use {user} for member name, {days} for streak lost and {guild} for guild name.")
async def change_text_loss(ctx: discord.Interaction, text):
    data = datastore.datastore.getdata(ctx.guild_id)
    if await check_eligibility(ctx, data):
        data["talkstreak"]["roles"]["loss_message"] = text[:MAX_TEXT_LENGTH]
        usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
        embed = discord.Embed(colour = usedcolor, title=f'Changed streak loss text', description=f"Changed text for a streak loss:\n{text}")
        message = await ctx.response.send_message(embed=embed, ephemeral=True)

@talkset.command(name="min_days_to_show", description="Changes amount of days needed for a streak to be displayed in member's name.")
@discord.option(name="days", type=int, description="Amount of days.")
async def change_text_loss(ctx: discord.Interaction, days):
    data = datastore.datastore.getdata(ctx.guild_id)
    if await check_eligibility(ctx, data):
        data["talkstreak"]["roles"]["min_show_streak"] = min(1024, days)
        usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
        embed = discord.Embed(colour = usedcolor, title=f'Changed minimum amount of days', description=f"Changed minimum amount of streak days before a streak will be shown to **{days}**")
        message = await ctx.response.send_message(embed=embed, ephemeral=True)

@talkadd.command(name="banned_channel", description="Adds a channel where streak won't be added.")
@discord.option(name="channel", type=discord.SlashCommandOptionType.channel, description="Channel to be blacklisted.")
async def ban_channel(ctx: discord.Interaction, channel):
    data = datastore.datastore.getdata(ctx.guild_id)
    if await check_eligibility(ctx, data):
        data["talkstreak"]["banned_channels"][str(channel.id)] = True
        usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
        embed = discord.Embed(colour = usedcolor, title=f'Banned a channel', description=f"Talking streak will no longer increase in <#{channel}>.")
        message = await ctx.response.send_message(embed=embed, ephemeral=True)


@talkremove.command(name="banned_channel", description="Removes a channel from those where streak won't be added.")
@discord.option(name="channel", type=discord.SlashCommandOptionType.channel, description="Channel to be removed from blacklist.")
async def ban_channel(ctx: discord.Interaction, channel):
    data = datastore.datastore.getdata(ctx.guild_id)
    if await check_eligibility(ctx, data):
        if str(channel) in data["talkstreak"]["banned_channels"]:
            del data["talkstreak"]["banned_channels"][str(channel.id)]
        usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
        embed = discord.Embed(colour = usedcolor, title=f'Banned a channel', description=f"Talking streak will no longer increase in <#{channel}>.")
        message = await ctx.response.send_message(embed=embed, ephemeral=True)

# -- ROLES --

@roleset.command(name="add", description="Adds a role reward.")
@discord.option(name="role", type=discord.SlashCommandOptionType.role, description="Role to add.")
@discord.option(name="days", type=int, description="Days needed to achieve a role.")
@discord.option(name="text", type=str, description="Custom award text. Use {user} for member name, {days} for user streak and {role} for role obtained.", default=None)
async def role_add(ctx: discord.Interaction, role: discord.role, days, text: str | None):
    data = datastore.datastore.getdata(ctx.guild_id)
    if await check_eligibility(ctx, data):
        d = {"days": days}
        if text and text != "":
            d["message_on_get"] = text[:MAX_TEXT_LENGTH]
        data["talkstreak"]["roles"][str(role.id)] = d
        usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
        embed = discord.Embed(colour = usedcolor, title=f'Added a role', description=f"Added a **@{role.name}** role as a reward for **{days}** 🔥 day talking streak.",
            footer=discord.EmbedFooter("View all role rewards using /view roles."))
        message = await ctx.response.send_message(embed=embed, ephemeral=True)

@roleset.command(name="remove", description="Removes a role reward.")
@discord.option(name="role", autocomplete=get_roles, description="Role to remove.")
async def role_remove(ctx: discord.Interaction, role: str):
    data = datastore.datastore.getdata(ctx.guild_id)
    if await check_eligibility(ctx, data):
        if role in data["talkstreak"]["roles"]:
            del data["talkstreak"]["roles"][role]
        role: discord.Role = ctx.guild.get_role(role)

        usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
        embed = discord.Embed(colour = usedcolor, title=f'Removed a role', description=f"Removed a **@{role.name}** role from talking streak rewards.")
        message = await ctx.response.send_message(embed=embed, ephemeral=True)


@roleset.command(name="change_text", description="Changes a text for a role obtainment.")
@discord.option(name="role", autocomplete=get_roles, description="Role to change text for.")
@discord.option(name="text", type=str, description="Custom award text. Use {user} for member name, {days} for user streak and {role} for role obtained.", default=None)
async def role_change_text(ctx: discord.Interaction, role: str, text):
    data = datastore.datastore.getdata(ctx.guild_id)
    if await check_eligibility(ctx, data):
        v = data["talkstreak"]["roles"][role]
        if text and text != "":
            v["message_on_get"] = text[:MAX_TEXT_LENGTH]
        elif "text" in v:
            del v["message_on_get"]
        role: discord.Role = ctx.guild.get_role(int(role))

        usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
        if text and text != "":
            text = text.replace("{days}", str(v["days"]))
            text = text.replace("{role}", f'<@&{role.id}>')
            embed = discord.Embed(colour = usedcolor, title=f'Changed obtainment text', description=f"Changed text for **<@&{role.id}>** role obtainment:\n{text}")
        else:
            embed = discord.Embed(colour = usedcolor, title=f'Removed', description=f"Removed text for **@{role.name}** role obtainment.")
        message = await ctx.response.send_message(embed=embed, ephemeral=True)

bot.add_application_command(talkedit)