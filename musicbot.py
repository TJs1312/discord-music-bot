import discord
import os
import yt_dlp as youtube_dl
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import asyncio

load_dotenv()
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="$", intents=intents)
song_queue = []

async def connect_voice_channel(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        return interaction.guild.voice_client

    channel = interaction.user.voice.channel
    voice_client = await channel.connect()
    return voice_client

async def play_song(interaction: discord.Interaction, song):
    voice_client = await connect_voice_channel(interaction)

    if voice_client.is_playing():
        await interaction.followup.send("A song is already playing. Wait for it to finish or use /skip.")
        return

    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(song, download=True)
            filepath = ydl.prepare_filename(info).replace('.webm', '.mp3')

            voice_client.play(
                discord.FFmpegPCMAudio(filepath),
                after=lambda e: bot.loop.create_task(cleanup_after_play(interaction, filepath, e))
            )
            await interaction.followup.send(f"Now playing: {info['title']}")
    except Exception as e:
        await interaction.followup.send(f"Error: {e}")

async def cleanup_after_play(interaction, filepath, error):
    if error:
        print(f"Playback error: {error}")

    await asyncio.sleep(1)

    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except PermissionError:
            print(f"Could not delete {filepath}")

    if song_queue:
        next_song = song_queue.pop(0)
        await play_song(interaction, next_song)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user} is online and commands are synced!")

@bot.tree.command(name="join")
async def join(interaction: discord.Interaction):
    if interaction.user.voice:
        await connect_voice_channel(interaction)
        await interaction.response.send_message("Joined your voice channel!")
    else:
        await interaction.response.send_message("You must be in a voice channel!")

@bot.tree.command(name="leave")
async def leave(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("Disconnected from voice channel.")
    else:
        await interaction.response.send_message("I am not in a voice channel.")

@bot.tree.command(name="play")
@app_commands.describe(url="URL of the song")
async def play(interaction: discord.Interaction, url: str):
    await interaction.response.defer()

    if not interaction.user.voice:
        await interaction.followup.send("You must be in a voice channel!")
        return

    song_queue.append(url)

    if not interaction.guild.voice_client or not interaction.guild.voice_client.is_playing():
        await play_song(interaction, song_queue.pop(0))
    else:
        await interaction.followup.send(f"Added to queue: {url}")

@bot.tree.command(name="pause")
async def pause(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.pause()
        await interaction.response.send_message("Paused the song.")
    else:
        await interaction.response.send_message("No song is playing.")

@bot.tree.command(name="resume")
async def resume(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client and voice_client.is_paused():
        voice_client.resume()
        await interaction.response.send_message("Resumed the song.")
    else:
        await interaction.response.send_message("No song is paused.")

@bot.tree.command(name="stop")
async def stop(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client:
        voice_client.stop()
        await voice_client.disconnect()
        await interaction.response.send_message("Stopped the music and disconnected.")
    else:
        await interaction.response.send_message("No song is playing.")

@bot.tree.command(name="skip")
async def skip(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await interaction.response.send_message("Skipped the song.")
    else:
        await interaction.response.send_message("No song is playing.")

@bot.tree.command(name="queue")
async def queue(interaction: discord.Interaction):
    if not song_queue:
        await interaction.response.send_message("The queue is empty.")
    else:
        queue_list = '\n'.join([f"{i+1}. {song}" for i, song in enumerate(song_queue)])
        await interaction.response.send_message(f"Queue:\n{queue_list}")

bot.run(DISCORD_BOT_TOKEN)
