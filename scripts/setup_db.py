#!/usr/bin/env python3
"""
Database initialization script for MemCode.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import init_database, check_database_connection
from utils.logger import setup_logging, get_logger

setup_logging("INFO")
logger = get_logger(__name__)


async def main():
    """Initialize the database."""
    logger.info("Starting database initialization...")
    
    # Check connection
    if not await check_database_connection():
        logger.error("Database connection failed!")
        sys.exit(1)
    
    # Initialize database
    await init_database()
    
    logger.info("Database initialization completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
