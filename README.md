# Hiver

Self-hosted Django app for interactive legal timelines, document archiving, and AI-assisted research.

## Setup

```bash
# Install dependencies
uv sync

# Initialize Rust submodule
git submodule update --init rust_did
cd rust_did && cargo build --release && cd ..

# Run migrations
python manage.py migrate

# Start server
python manage.py runserver
```

## Environment Variables

Create a `.env` file:

```
SECRET_KEY=your-secret-key
DEBUG=True
MISTRAL_API_KEY=your-api-key
```

## Apps

- `timeline/` - Vertical scrolling timeline with markdown upload
- `archive/` - Document processing and storage
- `messages/` - Conversation log integration
- `ai_assistant/` - AI research assistant (Mistral API)

## Theme

- Primary: Honey-Orange (#FF8C00)
- Accent: Byers Blue (#0064AA)
- Dark/Light mode toggle supported

## License

Byers Brands ecosystem