# Default data sample lo
defaultdata = {
    "guild_id": 0,
    "qotd": {
        "settings": {
            "save_removed_cards": True,
            "save_used_cards": False,
            "notify_suggestions": True,
        },
        "decks": dict(),
        "savedcards": dict(),
        "usedcards": dict(),
        "trusted": {"members": dict(), "roles": dict()}, 
        "max_suggestions": 100, 
        "suggestions": dict()
    },
    "talkstreak": {
        "settings": {
            "ping_member": True,
            "display_streak": True,
            "stack_roles": True,
            "save_roles": True,
            "set_fail_time": True,
        },
        "min_show_streak": 2,
        "cooldown": 72000,
        "fail_time": 100800,
        "trusted": {"members": dict(), "roles": dict()}, 
        "banned_channels": dict(),
        "roles": dict(),
        "streaks": dict(),
        "cd_check": dict(),
        "default_message": "**{user}** has achieved the daily talking streak of **{days}**🔥 days and got the role **{role}**!",
        "loss_message": "You have lost the daily talking streak of **{days}**🔥 days in **{guild}**!",
        "channel": 2, # 2 is for the same channel, 1 is for DMs, 0 is to disable
    },
    "modulesenabled": {
        "qotd": True,
        "talkstreak": True,
    },
    "misc": {
        "language": "EN",
        "color": [231, 158, 203],
    },
}

defaultsettings = {
    "display_streak": True,
    "dm_streak_loss": True,
}

classes = {
    "deck": {"name": "Forgot a name, silly!", "card_order": [], "id": "no id", "cards": dict(), "channel": 0, "post_cooldown": 86400, "cd_check": 1337, "disabled": False, 
             "post_mode": "FIFO", "max_cards": 200},
             # deck can also have: "paused": True,
    "role_talkstreak": {"id": 0, "days": 5, "message_on_get": "you got thing"}
}