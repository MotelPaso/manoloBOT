<div align="center">
  

# M.A.N.O.L.O

A Discord bot built for real use — tracks voice call time, manages voice channels, and lets you call out absent friends.


## Tech Stack
</div>

- **Python** with [discord.py](https://discordpy.readthedocs.io/)
- **PostgreSQL** for persistent data storage
- **asyncpg** for async database queries
- **Railway** for deployment

## Commands
| Command | Description |
|---|---|
| `/join` | Joins the user's current voice channel |
| `/disconnect` | Disconnects the bot from the voice channel |
| `/call @user` | DMs a member to let them know they're being called |
| `/stats` | Shows your total time spent in voice calls on this server |
| `/topstats` | Shows the top 5 members by voice call time on this server |

## Self-hosting

### Prerequisites
- Python 3.10+
- A PostgreSQL database
- A Discord bot token — create one at the [Discord Developer Portal](https://discord.com/developers/applications)

### Installation

```bash
git clone https://github.com/MotelPaso/M.A.N.O.L.O.git
cd M.A.N.O.L.O
pip install -r requirements.txt
```

### Configuration
Create a `.env` file in the root directory:
```
TOKEN=your_bot_token_here
DATABASE_URL=your_postgresql_connection_string_here
```

### Running
```bash
python main.py
```

## Deployment
This bot is designed to be deployed on [Railway](https://railway.app). Add a PostgreSQL database to your Railway project and set the `TOKEN` and `DATABASE_URL` environment variables.
