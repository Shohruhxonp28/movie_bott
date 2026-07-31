# Telegram Movie Bot

A clean, simple, and well-structured Telegram Movie Bot built with Python, aiogram 3.x, and SQLAlchemy ORM.

## Technologies Used

- Python 3.13+
- aiogram 3.x (Async Telegram Bot Framework)
- SQLAlchemy (ORM)
- asyncpg (PostgreSQL Async client)
- python-dotenv (Environment variables loader)
- RapidFuzz (Fuzzy spelling-tolerant search)

## Project Structure

```
app/
│
├── handlers/
│   ├── user.py
│   ├── admin.py
│   ├── callback.py
│
├── keyboards.py
├── database.py
├── models.py
├── states.py
├── config.py
├── utils.py
├── main.py
└── .env
```

## Setup & Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables**:
   Create a `.env` file inside the `app/` folder (or copy `app/.env` template) and fill in the details:
   ```env
   BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
   DATABASE_URL=postgresql+asyncpg://username:password@localhost/database_name
   ADMIN_IDS=123456789,987654321
   STORAGE_CHANNEL_ID=-1001234567890
   ```

3. **Database Initialization**:
   The bot automatically initializes the database tables on startup. Make sure your PostgreSQL instance is running and the database specified in `DATABASE_URL` exists.

## Running the Bot

To run the bot, execute the following command from the project root:

```bash
python -m app.main
```
