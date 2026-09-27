# A module responsible for questions of the day.

# Failsafes which, in case of a raid, won't let your PC get flooded with tons of trash data. Increase past default values at your own risk.
MAX_DECK_LIMIT = 50
MAX_CARD_LIMIT = 1000
MAX_SUGGESTIONS = 1500
MAX_DECK_NAME_LENGTH = 100
MAX_TEXT_LENGTH = 512

import re, time, uuid, asyncio, math
from random import randint
import discord
from discord.ext import commands
from discord.ui import Button, View
import datastore, shared

bot = shared.bot

boolchoice = [discord.OptionChoice(name="True", value="1"), discord.OptionChoice(name="False", value="0")]
postmodes = [discord.OptionChoice(name="First in, First out", value="FIFO"), discord.OptionChoice(name="Last in, First out", value="LIFO"), discord.OptionChoice(name="Shuffle", value="shuffle")]

multipliers = {"d": 86400, "h": 3600, "m": 60, "s": 1}
def convert_time(time: str):
    if time.isdigit():
        return int(time)
    time = time.replace(" ", "").lower()
    ans = 0
    for value, unit in re.findall(r"(\d+)([dhms])", time):
        ans += int(value) * multipliers[unit]
    return ans

def generate_id(folder: list):
    id = str(uuid.uuid1())[:5]
    while id in folder:
        id = str(uuid.uuid1())[:5]
    return id

async def post(data, deck):
    channel = bot.get_channel(deck["channel"])
    if not data["modulesenabled"]["qotd"]:
        return
    if not channel:
        print(f"A channel for deck {deck} was not found! Change it using /deck set channel.")
        return
    elif deck["disabled"]:
        embed = discord.Embed(colour = discord.Colour.red(), title="Error", description="A deck is disabled and therefore a card was not posted! ")
        message = await channel.send(embed=embed)
        return
    usedcolor = discord.Color.from_rgb(*data["misc"]["color"]) 
    if len(deck["card_order"]) > 0:
        if deck["post_mode"] == "shuffle":
            num = randint(0, len(deck["card_order"]))
        elif deck["post_mode"] == "FIFO":
            num = 0
        elif deck["post_mode"] == "LIFO":
            num = len(deck["card_order"])
        id = deck["card_order"].pop(num)
        card = deck["cards"][id]
        embed = discord.Embed(colour = usedcolor, title=f"{deck['name']}", description=card["text"],
                                footer=discord.EmbedFooter(f"Want to suggest a card? Use /suggest. -- {deck['id']} -- Cards left: {len(deck['card_order'])}"))
        if "image" in card:
            embed.set_image(card["image"])
        if data["qotd"]["settings"]["save_used_cards"]:
            p = id
            if p in data['qotd']['usedcards']:
                p = generate_id(data['qotd']['usedcards'])
            data['qotd']['usedcards'][p] = card.copy()
        del deck["cards"][id]
    else:
        deck["paused"] = True
        embed = discord.Embed(colour = usedcolor, title=f"{deck['name']} -- No cards left", description="A deck did not have any cards to post. It was set to paused until a card is added or moved to a deck.",
                                footer=discord.EmbedFooter(f"Add some cards using /card add. -- {deck['id']}"))
    message = await channel.send(embed=embed)


async def rifle(data, deck):
    try:
        timetowait = deck["cd_check"]-time.time()+deck["post_cooldown"]
        if timetowait > 0:
            rememberedtime = deck["cd_check"]
            await asyncio.sleep(timetowait)
            if deck["disabled"] or "paused" in deck:
                return
            if rememberedtime == deck["cd_check"]:
                deck["cd_check"] = math.ceil(time.time()+deck["post_cooldown"])
                await post(data, deck)
                await hang_a_rifle(data, deck)
            else:
                print("Attempted to post a card, but cd_check was changed beforehand.")
                if deck["cd_check"] > rememberedtime:
                    await hang_a_rifle(data, deck)
        else:
            if deck["disabled"] or "paused" in deck:
                return
            deck["cd_check"] = math.ceil(time.time()+deck["post_cooldown"])
            await post(data, deck)
            await hang_a_rifle(data, deck)
    except asyncio.CancelledError:
        pass

hanged_posts = dict()
async def hang_a_rifle(data, deck):
    i = deck["id"]
    if not data["modulesenabled"]["qotd"]:
        return
    if i in hanged_posts:
        hanged_posts[i].cancel()
    task = await rifle(data, deck)
    hanged_posts[i] = task

permissions = discord.SlashCommandGroup("qotd", "Commands to manage adding trusted members and roles for managing QOTD decks.")
suggestions = discord.SlashCommandGroup("suggestions", "Commands to review suggestions.")
deckgroup = discord.SlashCommandGroup("deck", "Commands to create and edit decks for QOTDs.")
deckset = deckgroup.create_subgroup("set", "Edits deck parameters.")
cardgroup = discord.SlashCommandGroup("card", "Commands to create and edit cards to use for decks.")
cardsset = cardgroup.create_subgroup("set", "Edits card parameters.")

# -- FUNCTIONS --

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
get_decks = gd(False)
get_decks_including_saved = gd(True)

def gc(getvoid=False):
    async def getcards(ctx: discord.AutocompleteContext):
        data = datastore.datastore.getdata(ctx.interaction.guild_id)
        values = []
        for v in data["qotd"]["decks"].values():
            for j in v['cards'].keys():
                values.append(discord.OptionChoice(name=f"#{j} -- {v['text']}", value=j))
        if getvoid and len(data["qotd"]["savedcards"]) > 0:
            for j in data["qotd"]["savedcards"].keys():
                values.append(discord.OptionChoice(name=f"#{j} -- Cards saved from deleted decks", value=j))
        if getvoid and len(data["qotd"]["usedcards"]) > 0:
            for j in data["qotd"]["usedcards"].keys():
                values.append(discord.OptionChoice(name=f"#{j} -- Cards already used", value=j))
        return [c for c in values if ctx.value.lower() in c.name.lower()][:25]
    return getcards
get_cards = gc(False)
get_cards_including_saved = gc(True)

def gs():
    async def getsuggestions(ctx: discord.AutocompleteContext):
        data = datastore.datastore.getdata(ctx.interaction.guild_id)
        values = []
        for j, d in data['qotd']['suggestions'].items():
            values.append(discord.OptionChoice(name=f"#{j} -- {d['text'][:65]}", value=j))
        return [c for c in values if ctx.value.lower() in c.name.lower()][:25]
    return getsuggestions
get_suggestions = gs()

async def check_eligibility(ctx: discord.Interaction, data):
    if ctx.user.id in data["qotd"]["trusted"]["members"] or ctx.channel.permissions_for(ctx.user).manage_guild or {i.id for i in ctx.user.roles} & {int(i) for i in data["qotd"]["trusted"]["roles"].keys()}:
        return True
    else:
        embed = discord.Embed(colour = discord.Colour.red(), title="Error", description="You don't have the permissions and you're not in trusted member list to use this command!")
        message = await ctx.response.send_message(embed=embed, ephemeral=True)
        return False

async def find_card(ctx: discord.Interaction, data, card):
    deck = None
    if card in data['qotd']['usedcards']:
        deck = data['qotd']['usedcards']
    elif card in data['qotd']['savedcards']:
        deck = data['qotd']['savedcards']
    else:
        for i in data['qotd']['decks'].values():
            if card in i['cards']:
                deck = i
    if not deck:
        embed = discord.Embed(colour = discord.Colour.red(), title='Error', description="A deck with this card was not found!")
        message = await ctx.response.send_message(embed=embed, ephemeral=True)
        return None
    return deck

# -- TRUSTED MEMBERS --

@permissions.command(name="add_member", description="Adds a trusted member to manage QOTD decks.")
@discord.option(name="member", type=discord.SlashCommandOptionType.user, description="Member to add to trusted list.")
async def addmember(ctx: discord.Interaction, member):
    data = datastore.datastore.getdata(ctx.guild_id)
    if ctx.channel.permissions_for(ctx.user).manage_guild:
        uniqueid = str(member.id)
        if uniqueid in data["qotd"]["trusted"]["members"]:
            embed = discord.Embed(colour = discord.Colour.red(), title="Error", description=f"**@{member.name}** is already in trusted member list, so they were not added.", thumbnail=member.avatar.url)
            message = await ctx.response.send_message(embed=embed, ephemeral=True)
        else:
            data["qotd"]["trusted"]["members"][uniqueid] = True
            usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
            embed = discord.Embed(colour = usedcolor, title="Added member", description=f"Added **@{member.name}** to trusted member list.", thumbnail=member.avatar.url)
            message = await ctx.response.send_message(embed=embed, ephemeral=True)
    else:
        embed = discord.Embed(colour = discord.Colour.red(), title="Error", description="You don't have the permissions to use this command!")
        message = await ctx.response.send_message(embed=embed, ephemeral=True)
        return False
            
@permissions.command(name="remove_member", description="Removes a trusted member from managing QOTD decks.")
@discord.option(name="member", type=discord.SlashCommandOptionType.user, description="Member to remove from trusted list.")
async def removemember(ctx: discord.Interaction, member):
    data = datastore.datastore.getdata(ctx.guild_id)
    if ctx.channel.permissions_for(ctx.user).manage_guild:
        uniqueid = str(member.id)
        if not uniqueid in data["qotd"]["trusted"]["members"]:
            embed = discord.Embed(colour = discord.Colour.red(), title="Error", description=f"**@{member.name}** is not in trusted member list.", thumbnail=member.avatar.url)
            message = await ctx.response.send_message(embed=embed, ephemeral=True)
        else:
            del data["qotd"]["trusted"]["members"][uniqueid]
            usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
            embed = discord.Embed(colour = usedcolor, title="Removed member", description=f"Removed **@{member.name}** from trusted member list.", thumbnail=member.avatar.url)
            message = await ctx.response.send_message(embed=embed, ephemeral=True)
    else:
        embed = discord.Embed(colour = discord.Colour.red(), title="Error", description="You don't have the permissions to use this command!")
        message = await ctx.response.send_message(embed=embed, ephemeral=True)
        return False

@permissions.command(name="add_role", description="Adds a trusted role to manage QOTD decks.")
@discord.option(name="role", type=discord.SlashCommandOptionType.role, description="Role to add to trusted list.")
async def addrole(ctx: discord.Interaction, role):
    data = datastore.datastore.getdata(ctx.guild_id)
    if ctx.channel.permissions_for(ctx.user).manage_guild:
        uniqueid = str(role.id)
        if uniqueid in data["qotd"]["trusted"]["roles"]:
            embed = discord.Embed(colour = discord.Colour.red(), title="Error", description=f"**<@{role.name}>** is already in trusted roles list, so it was not added.")
            message = await ctx.response.send_message(embed=embed, ephemeral=True)
        else:
            data["qotd"]["trusted"]["roles"][uniqueid] = True
            usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
            embed = discord.Embed(colour = usedcolor, title="Added role", description=f"Added **<@{role.name}>** to trusted role list.")
            message = await ctx.response.send_message(embed=embed, ephemeral=True)
    else:
        embed = discord.Embed(colour = discord.Colour.red(), title="Error", description="You don't have the permissions to use this command!")
        message = await ctx.response.send_message(embed=embed, ephemeral=True)
        return False
            
@permissions.command(name="remove_role", description="Removes a trusted role from managing QOTD decks.")
@discord.option(name="role", type=discord.SlashCommandOptionType.role, description="role to remove from trusted list.")
async def removerole(ctx: discord.Interaction, role):
    data = datastore.datastore.getdata(ctx.guild_id)
    if ctx.channel.permissions_for(ctx.user).manage_guild:
        uniqueid = str(role.id)
        if not uniqueid in data["qotd"]["trusted"]["roles"]:
            embed = discord.Embed(colour = discord.Colour.red(), title="Error", description=f"**<@{role.name}>** is not in trusted roles list.")
            message = await ctx.response.send_message(embed=embed, ephemeral=True)
        else:
            del data["qotd"]["trusted"]["roles"][uniqueid]
            usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
            embed = discord.Embed(colour = usedcolor, title="Removed role", description=f"Removed **<@{role.name}>** from trusted roles list.")
            message = await ctx.response.send_message(embed=embed, ephemeral=True)
    else:
        embed = discord.Embed(colour = discord.Colour.red(), title="Error", description="You don't have the permissions to use this command!")
        message = await ctx.response.send_message(embed=embed, ephemeral=True)
        return False

# -- CARDS --

@cardgroup.command(name="add", description="Adds a card to a deck.")
@discord.option(name="deck", autocomplete=get_decks, description="Deck to add the card into.")
@discord.option(name="text", description="Text this card will have.")
@discord.option(name="image", description="You can add an image to this card. PNGs, JPGs and GIFs are supported.", default=None)
async def card_add(ctx: discord.Interaction, deck, text, image: discord.Attachment | None):
    data = datastore.datastore.getdata(ctx.guild_id)
    if await check_eligibility(ctx, data):
        deck = data["qotd"]["decks"][deck]
        n, ml = deck["name"], deck["max_cards"]
        text = text[:MAX_TEXT_LENGTH]
        if image and len(image.url) > MAX_TEXT_LENGTH:
            embed = discord.Embed(colour = discord.Colour.red(), title="Error", description=f"URL length of ``{len(image.url)}`` exceeds the currently set limit of ``{MAX_TEXT_LENGTH}``. A new card was not added.",
                                footer=discord.EmbedFooter("This can only be changed by a bot host."))
            message = await ctx.response.send_message(embed=embed, ephemeral=True)
            return
        if len(deck["cards"]) >= deck["max_cards"]:
            embed = discord.Embed(colour = discord.Colour.red(), title="Error", description=f"Amount of cards in deck ``{n}`` exceeds the currently set limit of ``{ml}``. A new card was not added.",
                                footer=discord.EmbedFooter("Set the card limit using /deck set card_limit."))
            message = await ctx.response.send_message(embed=embed, ephemeral=True)
            return
        uniqueid = generate_id(deck['cards'])
        card = {"text": text}
        if image:
            card["image"] = image.url
        deck['cards'][uniqueid] = card
        deck["card_order"].append(uniqueid)
        if "paused" in deck:
            del deck["paused"]
            await hang_a_rifle(data, deck)
        usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
        c = deck["name"]
        embed = discord.Embed(colour = usedcolor, title=f'Card added: ``{uniqueid}``', footer = discord.EmbedFooter(text=f"Author: {ctx.user.name} -- Deck: {c}"),
                            description=text)
        if image:
            embed.image = image.url
        message = await ctx.response.send_message(embed=embed, ephemeral=True)

@cardgroup.command(name="move", description="Moves a card from deck to deck.")
@discord.option(name="card", autocomplete=get_cards_including_saved, description="A card to move.")
@discord.option(name="deck", autocomplete=get_decks, description="A deck to move a card into.")
async def card_move(ctx: discord.Interaction, card, deck):
    data = datastore.datastore.getdata(ctx.guild_id)
    if await check_eligibility(ctx, data):
        founddeck = await find_card(ctx, data, card)
        if founddeck:
            if "card_order" in founddeck:
                founddeck["card_order"].remove(card)
                foundcard = founddeck["cards"][card].copy()
                del founddeck["cards"][card]
            else:
                foundcard = founddeck[card].copy()
                del founddeck[card]
            deck = data["qotd"]["decks"][deck]
            if card in deck['cards']:
                card = generate_id(data['qotd']['usedcards'])
            deck['cards'][card] = foundcard
            deck["card_order"].append(card)
            
            if "paused" in deck:
                del deck["paused"]
                hang_a_rifle(data, deck)
            usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
            p = deck["name"]
            embed = discord.Embed(colour = usedcolor, title=f'Card moved: ``{card}``', description=f"A card was successfully moved to deck ``{p}``!")
            message = await ctx.response.send_message(embed=embed, ephemeral=True)

@cardsset.command(name="text", description="Changes text for a card.")
@discord.option(name="card", autocomplete=get_cards_including_saved, description="A card to change text for.")
@discord.option(name="text", type=str, description="Text to set for a card.")
async def card_set_text(ctx: discord.Interaction, card, text):
    data = datastore.datastore.getdata(ctx.guild_id)
    if await check_eligibility(ctx, data):
        founddeck = await find_card(ctx, data, card)
        if founddeck:
            text = text[:MAX_TEXT_LENGTH]
            if "card_order" in founddeck:
                founddeck['cards'][card]['text'] = text
            else:
                founddeck[card]['text'] = text
            usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
            embed = discord.Embed(colour = usedcolor, title=f'Card text changed: ``{card}``', description=f"A card's text was successfully changed:\n{text}")
            message = await ctx.response.send_message(embed=embed, ephemeral=True)

@cardsset.command(name="image", description="Changes image for a card, or removes it.")
@discord.option(name="card", autocomplete=get_cards_including_saved, description="A card to change image for.")
@discord.option(name="image", description="Image to set for a card. Leave blank to remove it.", default=None)
async def card_set_image(ctx: discord.Interaction, card, image: discord.Attachment | None):
    data = datastore.datastore.getdata(ctx.guild_id)
    if await check_eligibility(ctx, data):
        founddeck = await find_card(ctx, data, card)
        if founddeck:
            usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
            if image:
                if len(image.url) > MAX_TEXT_LENGTH:
                    embed = discord.Embed(colour = discord.Colour.red(), title="Error", description=f"URL length of ``{len(image.url)}`` exceeds the currently set limit of ``{MAX_TEXT_LENGTH}``. A new card was not added.",
                                    footer=discord.EmbedFooter("This can only be changed by a bot host."))
                    message = await ctx.response.send_message(embed=embed, ephemeral=True)
                    return
                if "card_order" in founddeck:
                    founddeck["cards"][card]['image'] = image.url
                else:
                    founddeck[card]['image'] = image.url
                embed = discord.Embed(colour = usedcolor, title=f'Card image changed: ``{card}``', description=f"A card's image was successfully changed.")
            else:
                if founddeck[card]['image']:
                    if "card_order" in founddeck:
                        del founddeck["cards"][card]['image']
                    else:
                        del founddeck[card]['image']
                    embed = discord.Embed(colour = usedcolor, title=f'Card image changed: ``{card}``', description=f"A card's image was successfully removed.")
                else:
                    embed = discord.Embed(colour = usedcolor, title=f'Nothing was changed for card ``{card}``', description=f"A card did not have an image, so there was nothing to remove.", footer = discord.EmbedFooter(text='If you wanted to add an image, put it into "image" option.'))
            message = await ctx.response.send_message(embed=embed, ephemeral=True)

@cardgroup.command(name="delete", description="Deletes a card from a deck.")
@discord.option(name="card", autocomplete=get_cards_including_saved, description="A card to delete.")
async def card_remove(ctx: discord.Interaction, card):
    data = datastore.datastore.getdata(ctx.guild_id)
    if await check_eligibility(ctx, data):
        deck = await find_card(ctx, data, card)
        if deck:
            if "card_order" in deck:
                deck["card_order"].remove(card)
                del deck["cards"][card]
            else:
                del deck[card]
            usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
            embed = discord.Embed(colour = usedcolor, title=f'Card deleted: ``{card}``', description="A card was successfully deleted!")
            message = await ctx.response.send_message(embed=embed, ephemeral=True)

# -- DECKS --

@deckgroup.command(name="create", description="Creates a deck to put question cards in.")
@discord.option(name="name", type=str, description="Name of a new deck.")
@discord.option(name="channel", type=discord.SlashCommandOptionType.channel, description="Channel in which QOTD from this deck will be posted.")
@discord.option(name="first_post_time", type=str, description='Delay before first QOTD will be posted. Use d/h/m/s format. (Example: "1d 2h 3m 4s".)')
@discord.option(name="post_cooldown", type=str, description='Cooldown between QOTD posting. Use d/h/m/s format. (Example: "1d 2h 3m 4s".)')
async def create(ctx: discord.Interaction, name, channel, first_post_time, post_cooldown):
    data = datastore.datastore.getdata(ctx.guild_id)
    if await check_eligibility(ctx, data):
        da = len(data["qotd"]["decks"])
        if da >= MAX_DECK_LIMIT:
            embed = discord.Embed(colour = discord.Colour.red(), title="Error", description=f"Amount of total decks ``{da+1}`` exceeds the currently set limit of ``{MAX_DECK_LIMIT}``. A new deck was not added.",
                                footer=discord.EmbedFooter("This can only be changed by the bot host."))
            return
        usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
        fpt = max(convert_time(first_post_time), 1)
        cd = max(convert_time(post_cooldown), 300)
        uniqueid = generate_id(data["qotd"]["decks"])
        deck = {"name": name, "cards": dict(), "id": uniqueid, "card_order": [], "channel": channel.id, "max_cards": 200, "post_cooldown": cd,
                "cd_check": time.time()+fpt, "disabled": False, "post_mode": "FIFO"}
        data["qotd"]["decks"][uniqueid] = deck
        await hang_a_rifle(data, deck)
        embed = discord.Embed(colour = usedcolor, title="Added new deck", footer = discord.EmbedFooter(text="Make sure to add some cards! Use /card add for that."),
                            description=f"Deck **{name}** has been successfully created!\n**Channel:**\n- <#{channel.id}>\n**Post cooldown:**\n``{cd}`` seconds (First post will happen on <t:{int(time.time()+fpt)}> (if a deck will have cards))")
        message = await ctx.response.send_message(embed=embed, ephemeral=True)

@deckgroup.command(name="post", description="Immediately triggers a QOTD post from a deck.")
@discord.option(name="deck", autocomplete=get_decks, description="Deck to post a QOTD from.")
async def insta_post(ctx: discord.Interaction, deck):
    data = datastore.datastore.getdata(ctx.guild_id)
    if await check_eligibility(ctx, data):
        usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
        await post(data, data["qotd"]["decks"][deck])

@deckgroup.command(name="shuffle", description=f"As it says, shuffles a deck.")
@discord.option(name="deck", autocomplete=get_decks, description="Deck to shuffle.")
async def deck_shuffle(ctx: discord.Interaction, deck):
    data = datastore.datastore.getdata(ctx.guild_id)
    if await check_eligibility(ctx, data):
        usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
        data['qotd']['decks'][deck]["card_order"].shuffle()
        embed = discord.Embed(colour = usedcolor, title="Deck shuffled",
                            description=f"Deck **{data['qotd']['decks'][deck]['name']}** has been successfully shuffled.")
        
@deckset.command(name="name", description="Changes a name for a deck.")
@discord.option(name="deck", autocomplete=get_decks, description="Deck to change name for.")
@discord.option(name="name", type=str, description="New name a deck will have.")
async def set_name(ctx: discord.Interaction, deck, name):
    data = datastore.datastore.getdata(ctx.guild_id)
    if await check_eligibility(ctx, data):
        usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
        embed = discord.Embed(colour = usedcolor, title="Deck name changed",
                            description=f"Deck **{data['qotd']['decks'][deck]['name']}** has been successfully renamed to **{name}**.")
        data["qotd"]["decks"][deck]["name"] = name
        message = await ctx.response.send_message(embed=embed, ephemeral=True)

@deckset.command(name="enabled", description="Changes a status for a deck. Disabled decks don't post QOTDs.")
@discord.option(name="deck", autocomplete=get_decks, description="Deck to change status for.")
@discord.option(name="enabled", choices=boolchoice, description="Will a deck be enabled?")
async def deck_set_enabled(ctx: discord.Interaction, deck, enabled):
    data = datastore.datastore.getdata(ctx.guild_id)
    if await check_eligibility(ctx, data):
        enabled = int(enabled)
        text = enabled and "enabled" or "disabled"
        usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
        if enabled:
            i = deck
            if i in hanged_posts:
                hanged_posts[i].cancel()
        embed = discord.Embed(colour = usedcolor, title=f"Deck ``{data['qotd']['decks'][deck]['name']}`` {text}",
                            description=f"Deck **{data['qotd']['decks'][deck]['name']}** has been successfully **{text}**. "+ (enabled and "QOTDs from this deck will be resumed." or "QOTDs from this deck will no longer be posted until you enable it."))
        data["qotd"]["decks"][deck]["disabled"] = not enabled
        message = await ctx.response.send_message(embed=embed, ephemeral=True)

@deckset.command(name="post_order", description="Changes a posting order for a deck.")
@discord.option(name="deck", autocomplete=get_decks, description="Deck to change posting order for.")
@discord.option(name="order", choices=postmodes, description="Posting order a deck will have.")
async def deck_set_order(ctx: discord.Interaction, deck, order):
    data = datastore.datastore.getdata(ctx.guild_id)
    if await check_eligibility(ctx, data):
        usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
        embed = discord.Embed(colour = usedcolor, title=f"Deck posting order changed",
                            description=f"Posting order for deck **{data['qotd']['decks'][deck]['name']}** has been successfully changed to **{order}**.")
        data["qotd"]["decks"][deck]["post_mode"] = order
        message = await ctx.response.send_message(embed=embed, ephemeral=True)

@deckset.command(name="channel", description="Changes a channel for a deck.")
@discord.option(name="deck", autocomplete=get_decks, description="Deck to change a channel for.")
@discord.option(name="channel", type=discord.SlashCommandOptionType.channel, description="A new channel QOTDs from this deck will be posted in.")
async def deck_set_channel(ctx: discord.Interaction, deck, channel):
    data = datastore.datastore.getdata(ctx.guild_id)
    if await check_eligibility(ctx, data):
        usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
        deck = data["qotd"]["decks"][deck]
        deck["channel"] = channel.id
        name = deck["name"]
        embed = discord.Embed(colour = usedcolor, title=f"Changed channels for deck ``{name}``",
                                        description=f"Deck {name} will now be posted in channel <#{channel.id}>.")
        message = await ctx.response.send_message(embed=embed, ephemeral=True)

@deckset.command(name="cooldown", description="Changes a cooldown between QOTD posts for a deck.")
@discord.option(name="deck", autocomplete=get_decks, description="Deck to change a cooldown for.")
@discord.option(name="post_cooldown", type=str, description='Cooldown between QOTD posting. Use d/h/m/s format. (Example: "1d 2h 3m 4s".)')
async def deck_set_cooldown(ctx: discord.Interaction, deck, cd):
    data = datastore.datastore.getdata(ctx.guild_id)
    if await check_eligibility(ctx, data):
        usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
        cd = convert_time(cd)
        deck = data["qotd"]["decks"][deck]
        deck["post_cooldown"] = cd
        deck["cd_check"] = math.ceil(time.time() + cd)
        name = deck["name"]
        await hang_a_rifle(data, deck)
        embed = discord.Embed(colour = usedcolor, title=f"Deck ``{name}`` cooldown changed",
                                        description=f"Cooldown for a deck ``{name}`` will now be ``{cd}`` seconds (Next post will happen on <t:{int(deck['cd_check'])}>.")
        message = await ctx.response.send_message(embed=embed, ephemeral=True)

@deckset.command(name="card_limit", description="Changes the maximum amount of cards a deck can have.")
@discord.option(name="deck", autocomplete=get_decks, description="Deck to change a limit for.")
@discord.option(name="amount", type=discord.SlashCommandOptionType.integer, description='How big the new limit will be (Default: 200).')
async def deck_set_card_limit(ctx: discord.Interaction, deck, amount):
    data = datastore.datastore.getdata(ctx.guild_id)
    if await check_eligibility(ctx, data):
        if amount > MAX_CARD_LIMIT:
            embed = discord.Embed(colour = discord.Colour.red(), title="Error", description=f"New card limit ``{amount}`` exceeds the currently maximum allowed limit of ``{MAX_CARD_LIMIT}`` set for a bot.",
                                footer=discord.EmbedFooter("This can only be changed by the bot host."))
        else:
            deck = data["qotd"]["decks"][deck]
            deck["max_cards"] = amount
            name = deck["name"]
            usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
            embed = discord.Embed(colour = usedcolor, title=f"Deck ``{name}`` max limit changed",
                                    description=f"Max amount of cards for deck ``{name}`` will now be ``{amount}``.")
        message = await ctx.response.send_message(embed=embed, ephemeral=True)

@deckset.command(name="suggestions_limit", description="Changes the maximum amount of active suggestions you can have.")
@discord.option(name="amount", type=discord.SlashCommandOptionType.integer, description='How big the new limit will be (Default: 100).')
async def deck_set_card_limit(ctx: discord.Interaction, deck, amount):
    data = datastore.datastore.getdata(ctx.guild_id)
    if await check_eligibility(ctx, data):
        if amount > MAX_SUGGESTIONS:
            embed = discord.Embed(colour = discord.Colour.red(), title="Error", description=f"New suggestion limit ``{amount}`` exceeds the currently maximum allowed limit of ``{MAX_SUGGESTIONS}`` set for a bot.",
                                footer=discord.EmbedFooter("This can only be changed by the bot host."))
        else:
            data["qotd"]["max_suggestions"] = amount
            usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
            embed = discord.Embed(colour = usedcolor, title=f"Suggestion limit changed",
                                    description=f"Max amount of active suggestions will now be ``{amount}``.")
        message = await ctx.response.send_message(embed=embed, ephemeral=True)

@deckgroup.command(name="clear", description="Deletes all cards in a deck.")
@discord.option(name="deck", autocomplete=get_decks_including_saved, description="Deck to clear.")
async def deck_clear(ctx: discord.Interaction, deck):
    data = datastore.datastore.getdata(ctx.guild_id)
    if await check_eligibility(ctx, data):
        yesbutton = Button(label="Yes", style=discord.ButtonStyle.green)
        view = View()
        view.add_item(yesbutton)

        message = None
        
        async def yescallback(interaction):
            nonlocal data, deck
            if deck == "0":
                description="Successfully cleared all saved cards!"
                cards = len(data["qotd"]["savedcards"])
                data["qotd"]["savedcards"].clear()
            elif deck == "1":
                description="Successfully cleared all used cards!"
                cards = len(data["qotd"]["usedcards"])
                data["qotd"]["usedcards"].clear()
            else:
                name = data["qotd"]["decks"][deck]["name"]
                cards = len(data["qotd"]["decks"][deck]["cards"])
                description=f"Successfully cleared deck **{name}**!"
                data["qotd"]["decks"][deck]["cards"].clear()
            
            usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
            yesembed = discord.Embed(colour = usedcolor, title="Deck cleared", description=description, footer = discord.EmbedFooter(text=f"***{cards}*** cards were deleted."))
        
            await interaction.response.send_message(embed=yesembed, ephemeral=True)

        yesbutton.callback = yescallback

        embed = discord.Embed(colour = discord.Color.red(), title="Deleting a deck", description=f"Are you sure you want to clear this deck?\n***This action is irreversible***.")
        message = await ctx.response.send_message(embed=embed, view=view, ephemeral=True)

@deckgroup.command(name="delete", description="Deletes a deck.")
@discord.option(name="deck", autocomplete=get_decks, description="Deck to be deleted.")
async def delete(ctx: discord.Interaction, deck):
    data = datastore.datastore.getdata(ctx.guild_id)
    if await check_eligibility(ctx, data):
        name = data['qotd']['decks'][deck]['name']
        
        yesbutton = Button(label="Yes", style=discord.ButtonStyle.green)
        view = View()
        view.add_item(yesbutton)

        async def yescallback(interaction):
            nonlocal data, name

            i = deck
            if i in hanged_posts:
                hanged_posts[i].cancel()
                
            l = len(data['qotd']['decks'][deck]["cards"])
            wastedcards = max(0, len(data['qotd']["savedcards"]) + l - MAX_CARD_LIMIT)
            if data['qotd']['settings']['save_removed_cards']:
                for i, v in data['qotd']['decks'][deck]["cards"].items():
                    if len(data['qotd']['savedcards']) > MAX_CARD_LIMIT:
                        break
                    if i in data['qotd']['savedcards']:
                        i = generate_id(data['qotd']['savedcards'])
                    data['qotd']['savedcards'][i] = v.copy()
            else:
                wastedcards = 0
            del data['qotd']['decks'][deck]
            usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
            yesembed = discord.Embed(colour = usedcolor, title="Deck deleted", description=f"Successfully deleted deck named **{name}**!")
            if wastedcards > 0:
                yesembed.set_footer(text=f"However, ***{wastedcards}*** cards were discarded since the limit of ***{MAX_CARD_LIMIT}*** cards saved from deleted decks was crossed. Clear or move them.")
            elif data['qotd']['settings']['save_removed_cards']:
                yesembed.set_footer(text=f"***{l}*** cards from this deck were saved into a special deck. They can be moved or deleted from there. This can also be disabled using /qotd save_cards.")
            await interaction.response.send_message(embed=yesembed, ephemeral=True)

        yesbutton.callback = yescallback

        embed = discord.Embed(colour = discord.Color.red(), title="Deleting a deck", description=f"Are you sure you want to delete deck named **{name}**?\n***This action is irreversible***.")
        message = await ctx.response.send_message(embed=embed, view=view, ephemeral=True)

# -- SUGGESTIONS --

@bot.slash_command(name="suggest", description="Suggests a card for daily questions.")
@discord.option(name="text", description="Text for a suggestion.")
@discord.option(name="image", description="Image to set for a card. Leave blank to remove it.", default=None)
async def suggest(ctx: discord.Interaction, text, image):
    data = datastore.datastore.getdata(ctx.guild_id)
    if len(data["qotd"]["suggestions"]) >= data["qotd"]["max_suggestions"]:
        embed = discord.Embed(colour = discord.Color.red(), title="Too many suggestions", description="A deck has too many suggestions at the moment! Maybe kindly ask moderators to review them :P")
        message = await ctx.response.send_message(embed=embed, ephemeral=True)
        return
    
    text = text[:MAX_TEXT_LENGTH]
    if image and len(image.url) > MAX_TEXT_LENGTH:
        embed = discord.Embed(colour = discord.Colour.red(), title="Error", description=f"URL length of ``{len(image.url)}`` exceeds the currently set limit of ``{MAX_TEXT_LENGTH}``. A new card was not added.",
                            footer=discord.EmbedFooter("This can only be changed by a bot host."))
        message = await ctx.response.send_message(embed=embed, ephemeral=True)
        return
    
    card = {"text": text[:1024], "author": ctx.user.id}
    if image:
        card["image"] = image.url

    id = generate_id(data["qotd"]["suggestions"])
    data["qotd"]["suggestions"][id] = card
    usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
    embed = discord.Embed(colour = usedcolor, title=f'Suggestion added: ``{id}``', description=text[:1024])
    message = await ctx.response.send_message(embed=embed, ephemeral=True)  

@suggestions.command(name="approve", description="Approves a card suggestion.")
@discord.option(name="suggestion", autocomplete=get_suggestions, description="A suggestion to be approved.")
@discord.option(name="deck", autocomplete=get_decks, description="Deck to put an approved card in.")
@discord.option(name="edit_text", type=str, description="You can immediately edit text for a card, if needed.", default=None)
async def sug_approve(ctx: discord.Interaction, suggestion, deck, text):
    data = datastore.datastore.getdata(ctx.guild_id)
    if await check_eligibility(ctx, data):
        keepimage = int(keepimage)
        deck = data["qotd"]["decks"][deck]
        if len(deck["cards"]) >= deck["max_cards"]:
            embed = discord.Embed(colour = discord.Colour.red(), title="Error", description=f"Amount of cards in deck ``{len(deck['cards'])}`` exceeds the currently set limit of ``{deck['max_cards']}``. A new card was not added.",
                                footer=discord.EmbedFooter("Set the card limit using /deck set card_limit."))
            message = await ctx.response.send_message(embed=embed, ephemeral=True)
            return
        if suggestion in deck["cards"]:
            suggestion = generate_id(deck["cards"])
        card = {"text": text or data["qotd"]["suggestions"][suggestion]}
        if "image" in data["qotd"]["suggestions"][suggestion]:
            card["image"] = data["qotd"]["suggestions"][suggestion]["image"]
        deck['cards'][suggestion] = card
        deck["card_order"].append(suggestion)
        if "paused" in deck:
            del deck["paused"]
            await hang_a_rifle(data, deck)
        usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
        c = deck["name"]
        embed = discord.Embed(colour = usedcolor, title=f'Suggestion approved: ``{data["qotd"]["suggestions"][suggestion]["text"]}``', 
                              footer = discord.EmbedFooter(text=f"Deck: {c}"),
                            description=data["qotd"]["suggestions"][suggestion])
        if "image" in data["qotd"]["suggestions"][suggestion]:
            embed.image = data["qotd"]["suggestions"][suggestion]["image"]
        message = await ctx.response.send_message(embed=embed, ephemeral=True)
        del data["qotd"]["suggestions"][suggestion]

@suggestions.command(name="deny", description="Denies a card suggestion.")
@discord.option(name="suggestion", autocomplete=get_suggestions, description="A suggestion to be declined.")
async def sug_deny(ctx: discord.Interaction, suggestion):
    data = datastore.datastore.getdata(ctx.guild_id)
    if await check_eligibility(ctx, data):
        for deck in data["qotd"]["decks"].values():
            if suggestion in data["qotd"]["suggestions"]:
                usedcolor = discord.Color.from_rgb(*data["misc"]["color"])
                c = deck["name"]
                embed = discord.Embed(colour = usedcolor, title=f'Suggestion denied: ``{suggestion}``', footer = discord.EmbedFooter(text=f"Deck: {c}"),
                                   description="A suggestion was denied.")
                message = await ctx.response.send_message(embed=embed, ephemeral=True)
                del data["qotd"]["suggestions"][suggestion]

bot.add_application_command(permissions)
bot.add_application_command(cardgroup)
bot.add_application_command(deckgroup)
bot.add_application_command(suggestions)
# my name is retep, and I am evil