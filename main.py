# This example requires the 'message_content' intent.

import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import asyncpg
import os
import time
load_dotenv()
token = os.getenv("TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

active_sessions = {}

class Client(commands.Bot):
    async def on_ready(self):
        print(f"Connecting to database:")
        self.db = await asyncpg.connect(DATABASE_URL)

        await self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS voice_stats (
                id BIGINT PRIMARY KEY,
                name TEXT NOT NULL,
                seconds_in_call REAL DEFAULT 0)
            """)
        print(f'We have logged in as {client.user}')
        try:
            synced = await self.tree.sync()
            print(f'synced {len(synced)} global commands')
        except Exception as e:
            print(f'Error in sync: {e}')
    async def on_message(self, message):
        if message.author == client.user:
            return
        if message.content == "ping":
            latency = client.latency * 1000
            await message.channel.send(f"ping: {round(latency,2)}ms")
    async def on_voice_state_update(self, member, before, after):
        current_time:float = time.time()
        if before.channel == None and after.channel != None: # was not in a channel and joined
            active_sessions[member.id] = current_time
        elif after.channel == None and before.channel != None: # left a channel
            if member.id not in active_sessions:
                return
            time_joined = active_sessions[member.id]
            duration = current_time - time_joined
            await self.db.execute(
                """
                INSERT INTO voice_stats (id, name, seconds_in_call) VALUES ($1, $2, $3)
                ON CONFLICT (id) DO UPDATE SET seconds_in_call = voice_stats.seconds_in_call + $3, name = $2
                """, member.id, member.name, duration)


intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True
client = Client(command_prefix="!", intents=intents)

@client.tree.command(name="join", description="Unir el bot al canal de voz del usuario")
async def join(interaction: discord.Interaction):
    user = interaction.user
    channel = interaction.channel
    if (user.voice == None):
        await channel.send("Que no estas en un canal tonto polla")
    elif (client.voice_clients != []):
        await channel.send("Ya estoy en un canal!")

    else:
        await interaction.response.send_message("Uniendome al canal...")
        voice_channel = user.voice.channel
        await voice_channel.connect(timeout=15, self_deaf=True)

@client.tree.command(name="disconnect", description="Sacar al bot del canal de voz")
async def disconnect(interaction: discord.Interaction):
    user = interaction.user
    channel = interaction.channel
    channel_list = client.voice_clients
    if (channel_list == []):
        await channel.send("El bot no esta conectado a ningun canal.")
    elif (user.voice == None): # usuario no conectado
        channel = interaction.channel
        await channel.send("Que no estas en un canal tonto polla")
    else:
        await interaction.response.send_message("Saliendo del canal...")
        current_channel = channel_list[0]
        await current_channel.disconnect()
        current_channel.cleanup()

@client.tree.command(name="call", description="Llama a un miembro del servidor")
async def call(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.send_message(f'llamando a {member.name}')
    try:
        await member.send(f'{member.name} TE ESTAN LLAMANDO CONTESTA!!!!!!!!!!!!')
    except Exception as e:
        print("error...")
        print(e)

client.run(token)