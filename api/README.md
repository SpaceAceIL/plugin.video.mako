# mako-api

Server-side resolver for Mako / Channel 12 live streams.

Made by **SpaceAce** - space@anan.media

## Endpoints

- GET /               - service info
- GET /health         - liveness probe
- GET /live           - resolve Channel 12
- GET /resolve?url=   - resolve any article

## Run

    pip install -r requirements.txt
    python app.py

## Docker

    docker build -t mako-api .
    docker run -p 5000:5000 mako-api

## License

GPL-2.0-only
