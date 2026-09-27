# File which executes everything else

import discord
from discord.ext import commands
from discord.ui import Button, View
import logging
from dotenv import load_dotenv
import os, asyncio
import PUTYOURTOKENANDIDHERE, shared
DISCORD_TOKEN = PUTYOURTOKENANDIDHERE.DISCORD_TOKEN
load_dotenv()

handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True

bot = discord.Bot(intents=intents)
shared.bot = bot

import datastore, qotd, talkingstreak

@bot.event
async def on_guild_join(guild):
    print(f"I was added to {guild}!")
    print("Make sure I have the permissions needed to function! Administrator permission also works, but you don't have to put it on if you don't trust me ;)")


@bot.event
async def on_ready():
    print('Bot is online, have fun! ^w^')
    print('Someone should send a message in a server to activate all running QOTD decks and talking streaks.')
    bot.loop.create_task(datastore.autosave())

@bot.event
async def on_message(message):
    if not message.author.bot:
        data = datastore.datastore.getdata(message.guild.id)
        if data['modulesenabled']['talkstreak']:
            asyncio.create_task(talkingstreak.message_func(message, data, bot))

async def check_eligibility(ctx: discord.Interaction):
    if ctx.channel.permissions_for(ctx.user).manage_guild:
        return True
    else:
        embed = discord.Embed(colour = discord.Colour.red(), title="Error", description="You don't have the permissions to use this command!")
        message = await ctx.response.send_message(embed=embed, ephemeral=True)
        return False

settings = discord.SlashCommandGroup("settings", "Set your, well, settings, LULZ!!")
miscset = discord.SlashCommandGroup("set", "Commands to edit miscellaneous.")
viewset = discord.SlashCommandGroup("view", "Commands to view stuff.")

@miscset.command(name="color", description="Sets embed color for all of bot's future embed messages.")
@discord.option(name="color", type=str, description="Color in rgb (Example: 255 255 255) color format.")
async def set_color(ctx: discord.Interaction, color):
    if await check_eligibility(ctx):
        usedcolor = None
        try:
            usedcolor = discord.Color.from_rgb(*[int(i) for i in color.split()])
        except:
            embed = discord.Embed(colour = discord.Colour.red(), title="Error", description="Color you've inputted is not supported! Use rgb (Example: 255 255 255) color format without commas.")
            message = await ctx.response.send_message(embed=embed, ephemeral=True)
        finally:
            yesbutton = Button(label="Yes", style=discord.ButtonStyle.green)
            view = View()
            view.add_item(yesbutton)

            message = None

            async def yescallback(interaction):
                nonlocal message
                datastore.datastore.getdata(interaction.guild_id)["misc"]["color"] = [int(i) for i in color.split()]
                yesembed = discord.Embed(colour = usedcolor, title="Changed embed color", description=f"Successfully changed embed color to rgb({color})!")
                await interaction.response.send_message(embed=yesembed, ephemeral=True)

            yesbutton.callback = yescallback

            embed = discord.Embed(colour = usedcolor, title="Changing embed color", description="Are you sure you want to change embed color? It will look like this from now on.")
            message = await ctx.response.send_message(embed=embed, view=view, ephemeral=True)

boolchoice = [discord.OptionChoice(name="True", value="1"), discord.OptionChoice(name="False", value="0")]

choicesqotd = [
    discord.OptionChoice(name="Save cards from deleted decks?", value="save_removed_cards"),
    discord.OptionChoice(name="Save cards that were posted?", value="save_used_cards"),
]
@settings.command(name="qotd", description="Edits the parameters for QOTD.")
@discord.option(name="parameter", choices=choicesqotd, description="A parameter to set.")
@discord.option(name="boolean", choices=boolchoice, description="Will it be enabled?")
async def set_qotd(ctx: discord.Interaction, parameter, boolean):
    if await check_eligibility(ctx):
        boolean = int(boolean)
        data = datastore.datastore.getdata(ctx.guild_id)
        data['qotd']['settings'][parameter] = boolean
        usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
        embed = discord.Embed(colour = usedcolor, title="Parameter changed", description=f"Parameter ``{parameter}`` was changed to ``{'True' if boolean else 'False'}``.")
        message = await ctx.response.send_message(embed=embed, ephemeral=True)

choicesstreak = [
    discord.OptionChoice(name="Stack role rewards? (if not, user will only have the highest one)", value="stack_roles"),
    discord.OptionChoice(name="Save roles even when user has lost their streak?", value="save_roles"),
    discord.OptionChoice(name="Ping member in addition to role award message?", value="ping_member"),
    discord.OptionChoice(name="Notify user when their talking streak is lost?", value="dm_streak_loss"),
    discord.OptionChoice(name="Prevent users from losing their talking streaks after bot goes offline?", value="dm_streak_loss"),
]
@settings.command(name="talk_streak", description="Edits the parameters for talking streak.")
@discord.option(name="parameter", choices=choicesstreak, description="A parameter to set.")
@discord.option(name="boolean", choices=boolchoice, description="Will it be enabled?")
async def set_qotd(ctx: discord.Interaction, parameter, boolean):
    if await check_eligibility(ctx):
        boolean = int(boolean)
        data = datastore.datastore.getdata(ctx.guild_id)
        data['talkstreak']['settings'][parameter] = boolean
        usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
        embed = discord.Embed(colour = usedcolor, title="Parameter changed", description=f"Parameter ``{parameter}`` was changed to ``{'True' if boolean else 'False'}``.")
        message = await ctx.response.send_message(embed=embed, ephemeral=True)

choicessettings = [
    discord.OptionChoice(name="Display streak right next to your name? (Example: name 25🔥)", value="display_streak"),
    discord.OptionChoice(name="Notify you when you lose your streak?", value="dm_streak_loss"),
    discord.OptionChoice(name="Notify a user when their suggestion is approved or denied?", value="notify_suggestions"),
]
@settings.command(name="self", description="Edits your parameters (can be used by anyone).")
@discord.option(name="parameter", choices=choicessettings, description="A parameter to set.")
@discord.option(name="boolean", choices=boolchoice, description="Will it be enabled?")
async def set_personal(ctx: discord.Interaction, parameter, boolean):
    boolean = True if int(boolean) else False
    datastore.datastore.setsetting(ctx.user.id, parameter, boolean)
    data = datastore.datastore.getdata(ctx.guild_id)
    usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
    embed = discord.Embed(colour = usedcolor, title="Parameter changed", description=f"Parameter ``{parameter}`` was changed to ``{'True' if boolean else 'False'}``.")
    message = await ctx.response.send_message(embed=embed, ephemeral=True)

enabledsettings = [
    discord.OptionChoice(name="Questions of the day", value="qotd"),
    discord.OptionChoice(name="Talking streak", value="talkstreak"),
]
@settings.command(name="enabled", description="Edits the state of a module (enabled or disabled?).")
@discord.option(name="module", choices=enabledsettings, description="A module to edit.")
@discord.option(name="boolean", choices=boolchoice, description="Will it be enabled?")
async def set_module(ctx: discord.Interaction, module, boolean):
    if await check_eligibility(ctx):
        boolean = int(boolean)
        data = datastore.datastore.getdata(ctx.guild_id)
        data['modulesenabled'][module] = boolean
        if boolean:
            if module == "qotd":
                for i in data["qotd"]["decks"].values():
                    asyncio.create_task(qotd.hang_a_rifle(data, i))
            else:
                asyncio.create_task(talkingstreak.professional_rifle_hanger(data))
        usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
        embed = discord.Embed(colour = usedcolor, title="Module status changed", description=f"Module was set to ``{'True' if boolean else 'False'}``.")
        message = await ctx.response.send_message(embed=embed, ephemeral=True)

# -- VIEW --

class Pages(discord.ui.View):
    def __init__(self, items, page_size, user, data, other={"title": str}) -> None:
        super().__init__(timeout=90)
        self.items = items
        self.page_size = page_size
        self.page = 0
        self.user = user
        self.data = data
        self.other = other

    def get_page_content(self):
        start = self.page * self.page_size
        end = start + self.page_size
        page_items = self.items[start:end]
        text = "".join(page_items)

        return discord.Embed(
            title=self.other["title"],
            footer=discord.EmbedFooter(f"Page {self.page + 1}/{self.total_pages} -- {len(self.items)} total"),
            description=text,
            color=discord.Color.from_rgb(*self.data["misc"]["color"])
        )
    
    @property
    def total_pages(self):
        return (len(self.items) - 1) // self.page_size + 1

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.user.id

    @discord.ui.button(label="⏮", style=discord.ButtonStyle.primary)
    async def first_page(self, button, interaction):
        self.page = 0
        await interaction.response.edit_message(embed=self.get_page_content(), view=self)

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.primary)
    async def previous_page(self, button, interaction):
        if self.page > 0:
            self.page -= 1
        await interaction.response.edit_message(embed=self.get_page_content(), view=self)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.primary)
    async def next_page(self, button, interaction):
        if self.page < self.total_pages - 1:
            self.page += 1
        await interaction.response.edit_message(embed=self.get_page_content(), view=self)

    @discord.ui.button(label="⏭", style=discord.ButtonStyle.primary)
    async def last_page(self, button, interaction):
        self.page = self.total_pages - 1
        await interaction.response.edit_message(embed=self.get_page_content(), view=self)
        
    @discord.ui.button(label="❌", style=discord.ButtonStyle.red)
    async def close(self, button, interaction: discord.Interaction):
        await interaction.message.delete()

@viewset.command(name="roles", description="Shows all role rewards.")
async def role_view(ctx: discord.Interaction):
    data = datastore.datastore.getdata(ctx.guild_id)
    roles = []
    for i, v in data["talkstreak"]["roles"].items():
        role: discord.Role = ctx.guild.get_role(int(i))
        roles.append(f"<@&{str(role.id)}> -- (**{v['days']}** 🔥 days)\n\n")
    view = Pages(roles, 6, ctx.user, data, {"title": "Roles obtainable from daily streak"})
    embed = view.get_page_content()
    message = await ctx.response.send_message(embed=embed, view=view)

@viewset.command(name="decks", description="Shows all decks.")
async def deck_view(ctx: discord.Interaction):
    data = datastore.datastore.getdata(ctx.guild_id)
    decks = []
    for i, v in data["qotd"]["decks"].items():
        decks.append(f"{v['disabled'] or 'paused' in v and '*Inactive -- *' or ''}**{v['name']}**\n*<#{str(v['channel'])}>, ({len(v['card_order'])} cards left*)\n\n")
    view = Pages(decks, 5, ctx.user, data, {"title": "Decks"})
    embed = view.get_page_content()
    message = await ctx.response.send_message(embed=embed, view=view)

def gd(getvoid=False):
    async def getdecks(ctx: discord.AutocompleteContext):
        data = datastore.datastore.getdata(ctx.interaction.guild_id)
        values = [discord.OptionChoice(name=f"{v['name']} -- #{ctx.interaction.guild.get_channel_or_thread(v['channel'])}", value=i) for i, v in data["qotd"]["decks"].items()]
        if getvoid and len(data["qotd"]["savedcards"]) > 0:
            values.append(discord.OptionChoice(name="Cards saved from deleted decks", value="0"))
        if getvoid and len(data["qotd"]["usedcards"]) > 0:
            values.append(discord.OptionChoice(name="Cards already used", value="1"))
        return [c for c in values if ctx.value.lower() in c.name.lower()][:25]
    return getdecks
get_decks = gd(True)

@viewset.command(name="cards", description="Shows all cards.")
@discord.option(name="deck", autocomplete=get_decks, description="Deck to show cards from.", default=None)
async def suggestion_view(ctx: discord.Interaction, deck):
    data = datastore.datastore.getdata(ctx.interaction.guild_id)
    cards = []
    if deck:
        if deck == "1":
            for i, v in data["qotd"]["usedcards"].items():
                cards.append(f"**#{i}** -- {v['text'][:100]}\n\n")
        elif deck == "0":
            for i, v in data["qotd"]["savedcards"].items():
                cards.append(f"**#{i}** -- {v['text'][:100]}\n\n")
        else:
            for i, v in data["qotd"]["decks"][deck]["cards"].items():
                cards.append(f"**#{i}** -- {v['text'][:100]}\n\n")
    else:
        for deck in data["qotd"]["decks"].values():
            for i, v in deck["cards"].items():
                cards.append(f"**#{i}** -- {v['text'][:100]}\nDeck: *{deck['name']}*\n\n")
        for i, v in data["qotd"]["usedcards"].items():
            cards.append(f"**#{i}** -- {v['text'][:100]}\n*Cards already used*\n\n")
        for i, v in data["qotd"]["savedcards"].items():
            cards.append(f"**#{i}** -- {v['text'][:100]}\n*Cards saved from deleted decks*\n\n")
    view = Pages(cards, 10, ctx.user, data, {"title": "Cards"})
    embed = view.get_page_content()
    message = await ctx.response.send_message(embed=embed, view=view)

@viewset.command(name="suggestions", description="Shows all suggestions.")
async def suggestion_view(ctx: discord.Interaction):
    data = datastore.datastore.getdata(ctx.guild_id)
    decks = []
    for i, v in data["qotd"]["suggestions"].items():
        user = ctx.guild.get_member(int(v["author"]))
        text = f"**#{i}** -- {v['text'][:350]}{'...' if len(v) > 350 else ''}\nAuthor: {user or '???'}{'image' in v and ' -- (has image)' or ''}\n\n"
        decks.append(text)
    view = Pages(decks, 5, ctx.user, data, {"title": "Suggestions"})
    embed = view.get_page_content()
    message = await ctx.response.send_message(embed=embed, view=view)

bot.add_application_command(settings)
bot.add_application_command(miscset)
bot.add_application_command(viewset)

bot.run(DISCORD_TOKEN)