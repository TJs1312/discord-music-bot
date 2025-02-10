import discord
import os
import yt_dlp as youtube_dl
from discord.ext import commands
from dotenv import load_dotenv
import asyncio  # Import asyncio for sleep

# Load environment variables from .env file
load_dotenv()
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# Set up the bot with necessary intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="$", intents=intents)

# Queue to manage songs
song_queue = []  # Renamed from 'queue' to 'song_queue'

# Function to connect to a voice channel
async def connect_voice_channel(ctx):
    if ctx.voice_client:
        return ctx.voice_client
    
    channel = ctx.author.voice.channel
    voice_client = await channel.connect()
    return voice_client

# Function to play a song
async def play_song(ctx, song):
    voice_client = await connect_voice_channel(ctx)

    # Check if already playing
    if voice_client.is_playing():
        await ctx.send("A song is already playing. Wait for it to finish or use the 'skip' command.")
        return

    # Options for downloading the song
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'outtmpl': 'downloads/%(title)s.%(ext)s',  # Save the file in a "downloads" folder
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(song, download=True)
            filepath = ydl.prepare_filename(info)
            filepath = filepath.replace('.webm', '.mp3')  # Change the extension if necessary

            # Play the downloaded file
            voice_client.play(
                discord.FFmpegPCMAudio(filepath),
                after=lambda e: bot.loop.create_task(cleanup_after_play(ctx, filepath, e))  # Clean up after playing
            )
            await ctx.send(f"Now playing: {info['title']}")
    except Exception as e:
        print(f"Error playing song: {e}")
        await ctx.send("An error occurred while trying to play the song.")

# Function to clean up after playing a song
async def cleanup_after_play(ctx, filepath, error):
    if error:
        print(f"An error occurred: {error}")
    
    # Wait for FFmpeg to release the file
    await asyncio.sleep(1)  # Add a small delay to ensure the file is released

    # Delete the file after playing it
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            print(f"Deleted file: {filepath}")
        except PermissionError:
            print(f"Could not delete file: {filepath} (still in use)")

    # Play the next song in the queue
    if song_queue:
        next_song = song_queue.pop(0)
        await play_song(ctx, next_song)

# Command to join a voice channel
@bot.command()
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
        await ctx.send(f'Joined the voice channel: {channel.name}')
    else:
        await ctx.send("You need to be in a voice channel for the bot to join!")

# Command to leave a voice channel
@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Disconnected from the voice channel.")
    else:
        await ctx.send("I am not connected to any voice channel.")

# Command to play a song
@bot.command()
async def play(ctx, url: str):
    if not ctx.author.voice:
        await ctx.send("You are not connected to a voice channel")
        return
    
    song_queue.append(url)  # Use 'song_queue' instead of 'queue'
    await ctx.send(f"Song added to queue: {url}! There are {len(song_queue)} songs in the queue.")

    if not ctx.voice_client or not ctx.voice_client.is_playing():
        await play_song(ctx, song_queue.pop(0))

# Command to pause the current song
@bot.command()
async def pause(ctx):
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_client and voice_client.is_playing():
        voice_client.pause()
        await ctx.send("Song paused")
    else:
        await ctx.send("No song is currently playing")

# Command to resume the paused song
@bot.command()
async def resume(ctx):
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_client and voice_client.is_paused():
        voice_client.resume()
        await ctx.send("Music resumed")
    else:
        await ctx.send("There is no music paused")

# Command to stop the song and disconnect
@bot.command()
async def stop(ctx):
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_client:
        voice_client.stop()
        await voice_client.disconnect()
        await ctx.send("Music stopped and bot disconnected")
    else:
        await ctx.send("There is no music playing.")

# Command to skip the current song
@bot.command()
async def skip(ctx):
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await ctx.send("Skipped to the next song")
    else:
        await ctx.send("No song is currently playing to skip")

# Command to display the queue
@bot.command()
async def queue(ctx):
    if not song_queue:
        await ctx.send("The queue is currently empty.")
    else:
        queue_list = "\n".join([f"{i+1}. {song}" for i, song in enumerate(song_queue)])
        await ctx.send(f"**Current queue:**\n{queue_list}")

# Command to display the help menu
@bot.command(name="commands")
async def help_command(ctx):
    help_message = """
    **Commands:**
    - `$join`: Joins the voice channel you are in.
    - `$leave`: Leaves the voice channel.
    - `$play <url>`: Adds a song to the queue and plays it.
    - `$pause`: Pauses the current song.
    - `$resume`: Resumes the paused song.
    - `$stop`: Stops the music and disconnects the bot.
    - `$skip`: Skips the current song.
    - `$queue`: Displays the current queue of songs.
    - `$commands`: Displays this help menu.
    """
    await ctx.send(help_message)

# Event when the bot is ready
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

# Command to play a test audio file - debugging purposes
@bot.command()
async def playtest(ctx):
    voice_client = await connect_voice_channel(ctx)
    url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"  # Test URL
    voice_client.play(discord.FFmpegPCMAudio(url))
    await ctx.send("Playing test audio.")

# Run the bot
bot.run(DISCORD_BOT_TOKEN)