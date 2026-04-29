# pymetal

A Pythonic interface for [Encyclopaedia Metallum](https://www.metal-archives.com/).

`pymetal` provides an easy-to-use API for searching bands, albums, and lyrics from the Encyclopaedia Metallum. It is built with `curl_cffi` to ensure reliable access and handles the complexities of web scraping and TLS fingerprinting out of the box.

## Quick Start

### Installation

```bash
pip install curl_cffi bs4 lxml
# Clone and install locally
pip install -e ./pymetal
```

### Basic Usage

```python
from pymetal import MetalArchives

m = MetalArchives()

# Get a random band
print(m.random_band())

# Search for lyrics
for lyrics in m.get_lyrics(song_title="Ace of Spades", band_name="Motorhead"):
    print(lyrics)
    break
```

## Documentation

Comprehensive documentation is available in the `/docs` directory:

- **[Getting Started](docs/getting_started.md)**: Installation and basic usage.
- **[Advanced Usage](docs/advanced_usage.md)**: Advanced search parameters and custom session handling.
- **[Developer Guide](docs/developer_guide.md)**: Architecture overview and how to contribute.
- **[API Reference](docs/api_reference.md)**: Detailed breakdown of classes and methods.

## Features

- **Encyclopaedia Metallum Support**: Full access to band data, discographies, and advanced search.
- **Modern Networking**: Uses `curl_cffi` for robust connection management.
- **Generator Based**: Designed for memory efficiency when processing large search results.

## License

This project is licensed under the MIT License - see the `LICENSE.md` file for details.
