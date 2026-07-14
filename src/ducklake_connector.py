import duckdb
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar
from dotenv import dotenv_values
import os
import typer
from rich.console import Console
from rich.panel import Panel


@dataclass
class DuckLakeConfig:
    """Configuration for connecting to DuckLake metadata."""
    DEFAULT_HOST: ClassVar[str] = "127.0.0.1"
    DEFAULT_PORT: ClassVar[int] = 5432
    DEFAULT_DATABASE: ClassVar[str] = "ducklake_catalog"
    DEFAULT_METADATA_SCHEMA: ClassVar[str] = "some_schema"
    DEFAULT_DATA_PATH: ClassVar[str] = ""
    DEFAULT_STORAGE_BACKEND: ClassVar[str] = "local"
    DEFAULT_S3_ENDPOINT: ClassVar[str] = ""
    DEFAULT_S3_BUCKET: ClassVar[str] = ""
    DEFAULT_S3_KEY_ID: ClassVar[str] = ""
    DEFAULT_S3_SECRET: ClassVar[str] = ""
    DEFAULT_S3_VERIFY_SSL: ClassVar[bool] = False
    ENV_HOST: ClassVar[str] = "DUCKLAKE_HOST"
    ENV_PORT: ClassVar[str] = "DUCKLAKE_PORT"
    ENV_DATABASE: ClassVar[str] = "DUCKLAKE_DATABASE"
    ENV_METADATA_SCHEMA: ClassVar[str] = "DUCKLAKE_METADATA_SCHEMA"
    ENV_DATA_PATH: ClassVar[str] = "DUCKLAKE_DATA_PATH"
    ENV_STORAGE_BACKEND: ClassVar[str] = "DUCKLAKE_STORAGE_BACKEND"
    ENV_S3_ENDPOINT: ClassVar[str] = "DUCKLAKE_S3_ENDPOINT"
    ENV_S3_BUCKET: ClassVar[str] = "DUCKLAKE_S3_BUCKET"
    ENV_S3_KEY_ID: ClassVar[str] = "DUCKLAKE_S3_KEY_ID"
    ENV_S3_SECRET: ClassVar[str] = "DUCKLAKE_S3_SECRET"
    ENV_S3_VERIFY_SSL: ClassVar[str] = "DUCKLAKE_S3_VERIFY_SSL"


    # Instance fields
    host: str = None
    port: int = None
    database: str = None
    metadata_schema: str = None
    data_path: str = None
    storage_backend: str = None
    s3_endpoint: str = None
    s3_bucket: str = None
    s3_key_id: str = None
    s3_secret: str = None
    s3_verify_ssl: bool = None

    def __post_init__(self):
        """Set defaults if not provided."""
        if self.host is None:
            self.host = self.DEFAULT_HOST
        if self.port is None:
            self.port = self.DEFAULT_PORT
        if self.database is None:
            self.database = self.DEFAULT_DATABASE
        if self.metadata_schema is None:
            self.metadata_schema = self.DEFAULT_METADATA_SCHEMA
        if self.storage_backend is None:
            self.storage_backend = self.DEFAULT_STORAGE_BACKEND
        self.storage_backend = self.storage_backend.strip().lower()
        if self.storage_backend not in {"local", "s3"}:
            raise ValueError(
                f"Invalid {self.ENV_STORAGE_BACKEND} in .env: {self.storage_backend}"
            )
        if self.s3_endpoint is None:
            self.s3_endpoint = self.DEFAULT_S3_ENDPOINT
        if self.s3_bucket is None:
            self.s3_bucket = self.DEFAULT_S3_BUCKET
        if self.s3_key_id is None:
            self.s3_key_id = self.DEFAULT_S3_KEY_ID
        if self.s3_secret is None:
            self.s3_secret = self.DEFAULT_S3_SECRET
        if self.s3_verify_ssl is None:
            self.s3_verify_ssl = self.DEFAULT_S3_VERIFY_SSL


    @property
    def resolved_data_path(self) -> str:
        if self.storage_backend == "s3":
            return f"s3://{self.s3_bucket}/"
        return self.data_path or ""

    @staticmethod
    def from_env_file(path: Path) -> "DuckLakeConfig":
        """Load DuckLake configuration from a .env file."""
        values = dotenv_values(path)
        host = values.get(DuckLakeConfig.ENV_HOST) or DuckLakeConfig.DEFAULT_HOST
        database = values.get(DuckLakeConfig.ENV_DATABASE) or DuckLakeConfig.DEFAULT_DATABASE
        metadata_schema = values.get(DuckLakeConfig.ENV_METADATA_SCHEMA) or DuckLakeConfig.DEFAULT_METADATA_SCHEMA
        data_path = values.get(DuckLakeConfig.ENV_DATA_PATH) or DuckLakeConfig.DEFAULT_DATA_PATH
        storage_backend = values.get(DuckLakeConfig.ENV_STORAGE_BACKEND) or DuckLakeConfig.DEFAULT_STORAGE_BACKEND
        s3_endpoint = values.get(DuckLakeConfig.ENV_S3_ENDPOINT) or DuckLakeConfig.DEFAULT_S3_ENDPOINT
        s3_bucket = values.get(DuckLakeConfig.ENV_S3_BUCKET) or DuckLakeConfig.DEFAULT_S3_BUCKET
        s3_key_id = values.get(DuckLakeConfig.ENV_S3_KEY_ID) or DuckLakeConfig.DEFAULT_S3_KEY_ID
        s3_secret = values.get(DuckLakeConfig.ENV_S3_SECRET) or DuckLakeConfig.DEFAULT_S3_SECRET

        raw_verify_ssl = values.get(DuckLakeConfig.ENV_S3_VERIFY_SSL)
        if raw_verify_ssl in (None, ""):
            s3_verify_ssl = DuckLakeConfig.DEFAULT_S3_VERIFY_SSL
        else:
            lowered = str(raw_verify_ssl).strip().lower()
            if lowered in {"1", "true", "yes", "y", "on"}:
                s3_verify_ssl = True
            elif lowered in {"0", "false", "no", "n", "off"}:
                s3_verify_ssl = False
            else:
                raise ValueError(
                    f"Invalid {DuckLakeConfig.ENV_S3_VERIFY_SSL} in .env: {raw_verify_ssl}"
                )
            
        raw_port = values.get(DuckLakeConfig.ENV_PORT)
        if raw_port in (None, ""):
            port = DuckLakeConfig.DEFAULT_PORT
        else:
            try:
                port = int(raw_port)
            except ValueError as exc:
                raise ValueError(f"Invalid {DuckLakeConfig.ENV_PORT} in .env: {raw_port}") from exc

        return DuckLakeConfig(
            host=host,
            port=port,
            database=database,
            metadata_schema=metadata_schema,
            data_path=data_path,
            storage_backend=storage_backend,
            s3_endpoint=s3_endpoint,
            s3_bucket=s3_bucket,
            s3_key_id=s3_key_id,
            s3_secret=s3_secret,
            s3_verify_ssl=s3_verify_ssl,
        )
    

console = Console()
    
#Returns the path to the .env file, either from an environment variable override or defaulting to the current working directory.
def env_file_path() -> Path:
    # Allow opt-in override for tests or advanced workflows.
    custom_path = os.environ.get("DL_TOOLS_ENV_FILE")
    if custom_path:
        return Path(custom_path)
    return Path.cwd() / ".env"

#Reads the database credentials (username and password) from the specified .env file. 
# It returns a tuple containing the username and password, or None for each if they are not found in the file.
def _read_credentials(path: Path) -> tuple[str | None, str | None]:
    values = dotenv_values(path)
    return values.get("DB_USERNAME"), values.get("DB_PASSWORD")

#Replaces single quotes with two single quotes. 
def _sql_literal(value: str) -> str:
    return value.replace("'", "''")
    
#Generates a list of SQL statements to set up the DuckLake connection using the provided username, password, and configuration.
def _ducklake_setup_sql(
    username: str,
    password: str,
    config: DuckLakeConfig,
) -> list[str]:
    return [
        (
            "CREATE OR REPLACE SECRET login_pg ("
            "TYPE postgres, "
            f"HOST '{_sql_literal(config.host)}', "
            f"PORT {config.port}, "
            f"DATABASE '{_sql_literal(config.database)}', "
            f"USER '{_sql_literal(username)}', "
            f"PASSWORD '{_sql_literal(password)}'"
            ");"
        ),
        (
            "CREATE OR REPLACE SECRET ducklake_s3 ("
            "TYPE s3, "
            "PROVIDER config, "
            f"KEY_ID '{_sql_literal(config.s3_key_id)}', "
            f"SECRET '{_sql_literal(config.s3_secret)}', "
            f"ENDPOINT '{_sql_literal(config.s3_endpoint)}', "
            "URL_STYLE 'path', "
            f"VERIFY_SSL '{str(config.s3_verify_ssl).lower()}'"
            ");"
        ),
        (
            "CREATE OR REPLACE SECRET my_ducklake ("
            "TYPE ducklake, "
            "metadata_path '', "
            f"metadata_schema '{_sql_literal(config.metadata_schema)}', "
            "metadata_parameters map {'TYPE': 'postgres', 'SECRET': 'login_pg'}"
            ");"
        ),
        (
            "ATTACH 'ducklake:my_ducklake' AS data ("
            f"DATA_PATH '{_sql_literal(config.data_path)}',"
            "OVERRIDE_DATA_PATH true"
            ");"
        ),
        "USE data;",
    ]

#Loads the database credentials from the .env file and checks if they are present.
#  If either the username or password is missing, it prints an error message and exits the program. 
# If both credentials are present, it returns them as a tuple.
def _load_credentials() -> tuple[str, str]:
    username, password = _read_credentials(env_file_path())
    if not username or not password:
        console.print(
            Panel.fit(
                "Missing DB credentials. Run [bold]config set[/bold] first to save DB_USERNAME/DB_PASSWORD.",
                style="red",
            )
        )
        raise typer.Exit(code=1)
    return username, password

#Loads the DuckLake configuration from the .env file, builds the necessary SQL statements to set up the DuckLake connection, 
# creates a DuckDB connection, and executes those statements.
def _connect_to_ducklake(config: DuckLakeConfig) -> duckdb.DuckDBPyConnection:
    missing = []
    if not config.s3_endpoint:
        missing.append(DuckLakeConfig.ENV_S3_ENDPOINT)
    if not config.s3_bucket:
        missing.append(DuckLakeConfig.ENV_S3_BUCKET)
    if not config.s3_key_id:
        missing.append(DuckLakeConfig.ENV_S3_KEY_ID)
    if not config.s3_secret:
        missing.append(DuckLakeConfig.ENV_S3_SECRET)
    if missing:
        console.print(
            Panel.fit(
                "Missing S3 configuration for DuckLake: "
                + ", ".join(missing)
                + ". Run [bold]config set[/bold] first.",
                style="red",
            )
        )
        raise typer.Exit(code=1)

    username, password = _load_credentials()
    setup_sql = _ducklake_setup_sql(username, password, config)
    connection = duckdb.connect()
    try:
        for statement in setup_sql:
            connection.execute(statement)
    except duckdb.Error:
        connection.close()
        raise
    return connection