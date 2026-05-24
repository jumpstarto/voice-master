# voice-master

A Discord bot that creates private, user-controlled voice channels on demand.

## Setup

### Environment Variables

| Variable        | Description                          |
|-----------------|--------------------------------------|
| `DISCORD_TOKEN` | Your Discord bot token (required)    |

Set `DISCORD_TOKEN` in your Railway service's environment variables. The bot will refuse to start and print a clear error if the variable is missing.

**Never hardcode your bot token in source code.**

## Railway Deployment

1. Fork or push this repo to GitHub.
2. Create a new Railway service from the repo.
3. Add `DISCORD_TOKEN` under **Variables** in the Railway dashboard.
4. Deploy — Railway will start `bot.py` automatically.

## Commands

| Command        | Description                                      |
|----------------|--------------------------------------------------|
| `-setup`       | (Admin) Creates the VoiceMaster category and join channel |
| `-leaderboard` | Shows the top 10 users by total voice time       |

## How it works

When a user joins the **➕ Join To Create** channel, the bot automatically creates a private voice channel and a paired text channel for that user. The owner can lock/unlock, rename, set a user limit, kick, mute, or unmute members via the control panel. Both channels are deleted when the last member leaves.
