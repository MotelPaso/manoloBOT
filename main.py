# This example requires the 'message_content' intent.

import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import yt_dlp as yt
import asyncpg
import os
import time
from typing import Literal
load_dotenv()
token = os.getenv("TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
active_sessions = {}

def format_time(seconds:int) -> str:
    minutes = seconds // 60
    hours = minutes // 60
    minutes = minutes % 60
    seconds = int(seconds % 60)
    return f"{round(hours)}h {round(minutes)}m {round(seconds)}s"

class Client(commands.Bot):
    async def on_ready(self):
        print(f"Connecting to database: ...")
        self.db = await asyncpg.connect(DATABASE_URL)
        await self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS voice_stats (
                id BIGINT,
                guild_id BIGINT,
                name TEXT NOT NULL,
                seconds_in_call REAL DEFAULT 0,
                PRIMARY KEY (id, guild_id))
            """)
        print(f'Connected! We have logged in as {client.user}')
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
                INSERT INTO voice_stats (id, guild_id, name, seconds_in_call) VALUES ($1, $2, $3, $4)
                ON CONFLICT (id, guild_id) DO UPDATE SET seconds_in_call = voice_stats.seconds_in_call + $4, name = $3
                """, member.id, member.guild.id, member.name, duration)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True
client = Client(command_prefix="!", intents=intents)

@client.tree.command(name="join", description="Unir el bot al canal de voz del usuario")
async def join(interaction: discord.Interaction):
    user = interaction.user
    if (user.voice == None):
        await interaction.response.send_message("Que no estas en un canal tonto polla")
        return
    voice_client = interaction.guild.voice_client
    if voice_client != None:
        await interaction.response.send_message("Ya estoy en un canal!")
    await interaction.response.send_message("Uniendome al canal...")
    voice_channel = user.voice.channel
    await voice_channel.connect(timeout=15, self_deaf=True)
    await interaction.channel.send(f"Me uni al canal {voice_channel.name}!")

@client.tree.command(name="disconnect", description="Sacar al bot del canal de voz")
async def disconnect(interaction: discord.Interaction):
    user = interaction.user
    channel_list = client.voice_clients
    if (channel_list == []): # TODO: this may work, needs testing
        await interaction.response.send_message("El bot no esta conectado a ningun canal.")
    elif (user.voice == None): # usuario no conectado
        await interaction.response.send_message("Que no estas en un canal tonto polla")
    else:
        await interaction.response.send_message("Saliendo del canal...")
        current_channel = channel_list[0]
        await current_channel.disconnect()
        current_channel.cleanup()

@client.tree.command(name="call", description="Llama a un miembro del servidor!")
async def call(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.send_message(f'llamando a {member.name}')
    try:
        await member.send(f'{member.name} TE ESTAN LLAMANDO CONTESTA!!!!!!!!!!!!')
    except Exception as e:
        print("error...")
        print(e)

@client.tree.command(name="stats", description="Revisa el tiempo que has pasado en una llamada!" )
async def stats(interaction: discord.Interaction):
    user = interaction.user
    user_stats = await client.db.fetch(
        "SELECT name, seconds_in_call FROM voice_stats WHERE (id = ($1) AND guild_id = ($2))", user.id, user.guild.id)
    response = f"Nombre: {user.name}\nTiempo pasado en llamada:"
    if not user_stats:
        await interaction.response.send_message(f"{response} 0s")
    else:
        time = format_time(int(user_stats[0]["seconds_in_call"]))
        await interaction.response.send_message(f"{response} {time} ")

@client.tree.command(name="topstats", description="Revisa las 5 personas con mayor tiempo en llamada del servidor!")
async def topstats(interaction: discord.Interaction):
    top_users = await client.db.fetch(
        "SELECT name, seconds_in_call FROM voice_stats WHERE (guild_id = ($1))" \
        "ORDER BY seconds_in_call DESC LIMIT 5", interaction.guild.id
    )
    top_print = "Top 5 usuarios con mayor tiempo en las llamadas:\n"
    i = 1
    for user in top_users:
        time = format_time(user['seconds_in_call'])
        top_print += f"{i}. {user['name']}: {time}\n"
        i += 1

    await interaction.response.send_message(top_print)

@client.tree.command(name="play_link", description="Ingresa un link de Youtube y toca una cancion.")
async def play_link(interaction: discord.Interaction, link_video:str):
    user = interaction.user
    if (user.voice == None):
        await interaction.response.send_message("Que no estas en un canal tonto polla")
        return
    voice_channel = user.voice.channel
    voice_client = interaction.guild.voice_client
    if voice_client == None:
        await interaction.response.send_message("No puedo poner musica en un canal de texto tio")
        return
    if voice_client.channel != voice_channel:
        await interaction.response.send_message("No estoy en tu mismo canal trol")
        return
    options = {'format': 'worstaudio'}
    with yt.YoutubeDL(options) as ydl:
        info = ydl.extract_info(link_video, download=False)
        url = info["url"]
        title = info["title"]
    voice_client.play(discord.FFmpegPCMAudio(url, before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', options='-vn'))
    await interaction.response.send_message(f"Sonando: {title}")

@client.tree.command(name='pause', description="Pone pausa a la cancion que este sonando!")
async def pause(interaction: discord.Interaction):
    voice = interaction.guild.voice_client
    if voice == None:
        await interaction.response.send_message("No estoy en ningun canal")
        return
    if voice.is_playing():
        voice.pause()
        await interaction.response.send_message("Musica en pausa.")
    else:
        await interaction.response.send_message("Pero si no esta sonando nada trol")

@client.tree.command(name="resume", description="Resume la musica que estaba sonando")
async def resume(interaction: discord.Interaction):
    voice = interaction.guild.voice_client
    if voice == None:
        await interaction.response.send_message("No estoy en ningun canal")
        return
    if voice.is_paused():
        voice.resume()
        await interaction.response.send_message("Despausada!")
    elif voice.is_playing():
        await interaction.response.send_message("Pero si no esta en pausa")

@client.tree.command(name="stop", description="Para la musica")
async def stop(interaction: discord.Interaction):
    voice = interaction.guild.voice_client
    if voice == None:
        await interaction.response.send_message("No estoy en ningun canal")
        return
    if voice.is_playing() or voice.is_paused():
        voice.stop()
        await interaction.response.send_message("Musica detenida.")
    else:
        await interaction.response.send_message("No habia nada sonando (creo que esto nunca puede pasar)")

@client.tree.command(name="help", description="Muestra los comandos disponibles / Shows available commands")
async def help(interaction: discord.Interaction, language: Literal["es", "en"]):
    if language == "es":
        response = """
        **M.A.N.O.L.O - Comandos disponibles**

        **Voz**
        `/join` — Me uno a tu canal de voz
        `/disconnect` — Me desconecto del canal de voz

        **Música**
        `/play_link [url]` — Pone una canción de YouTube
        `/pause` — Pausa la canción
        `/resume` — Reanuda la canción
        `/stop` — Para la música

        **Estadísticas**
        `/stats` — Muestra tu tiempo total en llamadas
        `/topstats` — Top 5 usuarios con más tiempo en llamadas

        **Otros**
        `/call [@usuario]` — Le manda un mensaje al usuario para que se conecte al discord
        `/help [idioma]` — Muestra este mensaje
        """
    else:
        response = """
        **M.A.N.O.L.O - Available commands**

        **Voice**
        `/join` — Joins your voice channel
        `/disconnect` — Disconnects from the voice channel

        **Music**
        `/play_link [url]` — Plays a YouTube song
        `/pause` — Pauses the current song
        `/resume` — Resumes the current song
        `/stop` — Stops the music

        **Stats**
        `/stats` — Shows your total time spent in voice calls
        `/topstats` — Top 5 users by time spent in voice calls

        **Other**
        `/call [@user]` — DMs a member to let them know they're being called
        `/help [language]` — Shows this message
        """
    await interaction.response.send_message(response)

client.run(token)