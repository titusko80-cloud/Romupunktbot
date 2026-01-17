#!/usr/bin/env python3
"""
Setup script for ROMUPUNKT bot metadata in multiple languages
Configures bot description, about text, and short description
"""

import os
import asyncio
from telegram import Bot
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    print("Error: BOT_TOKEN not found in .env file")
    exit(1)

async def setup_bot_metadata():
    """Configure bot profile information for multiple languages"""
    bot = Bot(token=BOT_TOKEN)
    
    print("Setting up ROMUPUNKT bot metadata...")
    
    # Descriptions for empty chat window
    descriptions = {
        'et': "🏎️ ROMUPUNKT – Müü oma vana või avariiline auto kiirelt ja mugavalt!\nVajuta START, et alustada.",
        'ru': "🏎️ ROMUPUNKT – Продай свой старый или аварийный автомобиль быстро и удобно!\nНажми START.",
        'en': "🏎️ ROMUPUNKT – Sell your old or damaged car fast and legally!\nPress START to begin."
    }
    
    # About text for profile page bio
    about_texts = {
        'et': "🏎️ ROMUPUNKT\n\nOleme ametlik lammutusteenus, kes ostab vanu ja avariilisi sõidukeid üle Eesti. Pakume kiiret hinnapakkumist ja professionaalset teenindust.\n\n✅ Võimalik kaasa võtta lammutustõend\n✅ Tasuline väljavedu\n✅ Kiired maksed\n\nAlusta vestlust, et saada pakkumine!",
        'ru': "🏎️ ROMUPUNKT\n\nМы — официальная служба утилизации, покупающая старые и аварийные автомобили по всей Эстонии. Предлагаем быстрое предложение и профессиональное обслуживание.\n\n✅ Возможность получить справку о ликвидации\n✅ Платный вывоз\n✅ Быстрые платежи\n\nНачните диалог, чтобы получить предложение!",
        'en': "🏎️ ROMUPUNKT\n\nWe are an official dismantling service buying old and damaged vehicles across Estonia. We offer fast pricing and professional service.\n\n✅ Destruction certificate available\n✅ Paid pickup service\n✅ Quick payments\n\nStart a chat to get your offer!"
    }
    
    # Short descriptions for sharing/profile summary
    short_descriptions = {
        'et': "🏎️ ROMUPUNKT – Müü oma auto kiiresti ja mugavalt!",
        'ru': "🏎️ ROMUPUNKT – Продай свой автомобиль быстро и удобно!",
        'en': "🏎️ ROMUPUNKT – Sell your car fast and legally!"
    }
    
    # Set descriptions for each language
    for lang_code, text in descriptions.items():
        try:
            await bot.set_my_description(text, language_code=lang_code)
            print(f"✅ Description set for language: {lang_code}")
        except Exception as e:
            print(f"❌ Failed to set description for {lang_code}: {e}")
    
    # Set about texts for each language
    for lang_code, text in about_texts.items():
        try:
            await bot.set_my_about_text(text, language_code=lang_code)
            print(f"✅ About text set for language: {lang_code}")
        except Exception as e:
            print(f"❌ Failed to set about text for {lang_code}: {e}")
    
    # Set short descriptions for each language
    for lang_code, text in short_descriptions.items():
        try:
            await bot.set_my_short_description(text, language_code=lang_code)
            print(f"✅ Short description set for language: {lang_code}")
        except Exception as e:
            print(f"❌ Failed to set short description for {lang_code}: {e}")
    
    print("\n✨ Bot metadata setup complete!")
    
    # Get bot info to verify
    try:
        bot_info = await bot.get_me()
        print(f"\n🤖 Bot Info:")
        print(f"   Name: {bot_info.first_name}")
        print(f"   Username: @{bot_info.username}")
        print(f"   ID: {bot_info.id}")
    except Exception as e:
        print(f"❌ Failed to get bot info: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(setup_bot_metadata())
    except KeyboardInterrupt:
        print("\nSetup cancelled by user")
    except Exception as e:
        print(f"❌ Setup failed: {e}")
