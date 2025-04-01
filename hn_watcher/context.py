from pika.exchange_type import ExchangeType

from hn_watcher.config import load_config
from hn_watcher.db import CommentDatabase
from hn_watcher.hn import HNContext, RequestsClient
from hn_watcher.publisher import PikaPublisher


class HNContextProvider:
    """
    Service locator/provider for Hacker News contexts.
    Follows the patterns in "Architecture Patterns with Python".
    """

    @staticmethod
    def get_default_context(config_path: str = "hn_watcher.toml") -> HNContext:
        """
        Factory method to create a default context with standard configuration.

        Args:
            config_path: Path to the configuration file. If not provided,
                         the function will search for a config file in standard locations.

        Returns:
            A configured HNContext
        """
        # Load configuration
        config = load_config(config_path)

        # Extract configuration values
        db_path = config["database"]["path"]
        rabbitmq_host = config["rabbitmq"]["host"]
        rabbitmq_exchange = config["rabbitmq"]["exchange"]
        rabbitmq_exchange_type = config["rabbitmq"]["exchange_type"]
        rabbitmq_durable = config["rabbitmq"]["durable"]
        rabbitmq_username = config["rabbitmq"]["username"]
        rabbitmq_password = config["rabbitmq"]["password"]
        request_delay = config["api"]["request_delay"]
        base_url = config["api"]["base_url"]

        # Create components
        db = CommentDatabase(db_path)
        api_client = RequestsClient()
        publisher = PikaPublisher(
            host=rabbitmq_host,
            exchange=rabbitmq_exchange,
            exchange_type=rabbitmq_exchange_type,
            durable=rabbitmq_durable,
            username=rabbitmq_username,
            password=rabbitmq_password,
        )

        return HNContext(
            api_client=api_client,
            db=db,
            publisher=publisher,
            request_delay=request_delay,
            base_url=base_url,
        )

    @staticmethod
    def get_context_from_params(
        db_path: str = "hn_comments.db",
        rabbitmq_host: str = "localhost",
        rabbitmq_exchange: str = "hackernews",
        rabbitmq_exchange_type: ExchangeType = ExchangeType.topic,
        rabbitmq_durable: bool = True,
        request_delay: float = 0.1,
        base_url: str = "https://hacker-news.firebaseio.com/v0",
    ) -> HNContext:
        """
        Alternative factory method that creates a context using parameter values directly.

        This method is provided for backwards compatibility and testing.

        Args:
            db_path: Path to the SQLite database file
            rabbitmq_host: RabbitMQ server hostname
            rabbitmq_exchange: RabbitMQ exchange name
            rabbitmq_exchange_type: RabbitMQ exchange type
            rabbitmq_durable: Whether the RabbitMQ exchange should be durable
            request_delay: Delay between API requests
            base_url: Base URL for the Hacker News API

        Returns:
            A configured HNContext
        """
        db = CommentDatabase(db_path)
        api_client = RequestsClient()
        publisher = PikaPublisher(
            host=rabbitmq_host,
            exchange=rabbitmq_exchange,
            exchange_type=rabbitmq_exchange_type,
            durable=rabbitmq_durable,
        )

        return HNContext(
            api_client=api_client,
            db=db,
            publisher=publisher,
            request_delay=request_delay,
            base_url=base_url,
        )
