#!/usr/bin/env python3
"""
Debug script to find the real admin notification function
"""

import inspect
import logging

# Setup logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

def debug_admin_notifier():
    """Debug function to find the real admin notifier"""
    logger.error("🔥 DEBUG SCRIPT FILE: %s", inspect.getfile(inspect.currentframe()))
    print("🔥 DEBUG SCRIPT FILE: %s" % inspect.getfile(inspect.currentframe()))
    print("If you see this, the debug script is working")

if __name__ == "__main__":
    debug_admin_notifier()
