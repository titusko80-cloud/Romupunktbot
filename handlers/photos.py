"""
Photo collection handler - Handle image uploads and storage
"""

from telegram import Update
from telegram.ext import ContextTypes
from states import PHOTOS, PHONE
import os
from datetime import datetime

async def photo_collection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle photo uploads"""
    # Initialize photo count if not exists
    if 'photo_count' not in context.user_data:
        context.user_data['photo_count'] = 0
        context.user_data['photos'] = []
    
    # Get the largest photo file
    photo_file = await update.message.photo[-1].get_file()
    
    # Create photos directory if it doesn't exist
    os.makedirs('photos', exist_ok=True)
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    user_id = update.effective_user.id
    filename = f"photos/{user_id}_{timestamp}_{context.user_data['photo_count'] + 1}.jpg"
    
    # Download and save photo
    await photo_file.download_to_drive(filename)
    
    # Store photo info
    context.user_data['photos'].append(filename)
    context.user_data['photo_count'] += 1
    
    if context.user_data.get('language') == 'ee':
        msg = f"Photo {context.user_data['photo_count']} saadetud! "
        if context.user_data['photo_count'] < 3:
            msg += f"Palun saatke veel {3 - context.user_data['photo_count']} fotot."
        elif context.user_data['photo_count'] == 3:
            msg += "Viimane foto on valikuline, kui soovite veel ühte."
        else:
            msg = "Kõik fotod on saadetud! Aitäh."
    else:
        msg = f"Photo {context.user_data['photo_count']} received! "
        if context.user_data['photo_count'] < 3:
            msg += f"Please send {3 - context.user_data['photo_count']} more photos."
        elif context.user_data['photo_count'] == 3:
            msg += "One more photo is optional if you'd like to add it."
        else:
            msg = "All photos received! Thank you."
    
    await update.message.reply_text(msg)
    
    # If we have enough photos, ask for contact info
    if context.user_data['photo_count'] >= 3:
        if context.user_data.get('language') == 'ee':
            msg = "Täname fotode eest! Viimane samm:\n\nPalun sisestage oma telefoninumber, et me saaksime teile kiirelt pakkumise teha:"
        else:
            msg = "Thank you for the photos! Final step:\n\nPlease enter your phone number so we can quickly send you an offer:"
        
        await update.message.reply_text(msg)
        return PHONE
    
    return PHOTOS
