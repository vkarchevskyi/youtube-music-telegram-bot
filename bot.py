import os
import yt_dlp
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, FSInputFile
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv('API_TOKEN')

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()

download_folder = 'downloads'
if not os.path.exists(download_folder):
    os.makedirs(download_folder)

async def download_and_send_audio(chat_id, url, playlist_index=None):
    if playlist_index is not None:
        outtmpl = f'{download_folder}/{playlist_index} - %(title)s.%(ext)s'
    else:
        outtmpl = f'{download_folder}/%(title)s.%(ext)s'

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': outtmpl,
        'noplaylist': True,
        'extractaudio': True,
        'writethumbnail': True,
        'audioformat': 'mp3',
        'postprocessors': [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            },
            {'key': 'EmbedThumbnail'},
            {'key': 'FFmpegMetadata'},
        ],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        file_name = ydl.prepare_filename(info_dict).replace('.webm', '.mp3').replace('.m4a', '.mp3')
        await bot.send_audio(chat_id, audio=FSInputFile(file_name, filename=file_name), title=info_dict.get('title'))
        os.remove(file_name)  # Clean up after sending

async def get_all_playlist_videos(chat_id, url):
    ydl_opts = {
        'quiet': True,  # Suppresses output from yt-dlp
        'flat_playlist': True,  # Use flat playlist mode to list video IDs
        'extract_flat': True,  # Extract only video IDs
        'force_generic_extractor': True  # Ensure the generic extractor is used
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # Extract video IDs from the URL
        result = ydl.extract_info(url, download=False)
        video_ids = [entry['id'] for entry in result['entries']]

        for index, video_id in enumerate(video_ids, start=1):
            video_url = f'https://youtube.com/watch?v={video_id}'
            await download_and_send_audio(chat_id, video_url, str(index).zfill(2))
            await asyncio.sleep(1)

@dp.message(CommandStart())
async def send_welcome(message: Message):
    await message.reply("Send me a YouTube playlist URL, and I'll download the audio tracks for you!")

@router.message(F.text.regexp(r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/playlist\?list=([a-zA-Z0-9_-]+)'))
async def handle_playlist(message: Message):
    url = message.text.strip()
    await message.reply("Downloading and converting playlist. This may take a while...")
    await get_all_playlist_videos(message.chat.id, url)

@router.message(F.text.regexp(r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})|(?:https?:\/\/)?youtu\.be\/([a-zA-Z0-9_-]{11})'))
async def handle_video(message: Message):
    url = message.text.strip()
    await message.reply("Downloading and converting audio. This may take a while...")
    await download_and_send_audio(message.chat.id, url)

# Register the router
dp.include_router(router)

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
