from pydantic import BaseModel, SecretStr
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)
from sqlalchemy import URL


class WarningLettersRetrieverConfig(BaseModel):
    url: str
    fda_url: str
    headers: dict
    crawl_delay: float

class FDAFilesConfig(BaseModel):
    inspections: str
    citations: str
    compliance_actions: str
    published483s: str
    recalls: str


class FDAIngestionConfig(BaseModel):
    path: str
    files: FDAFilesConfig


class DatabaseConfig(BaseModel):
    host: str
    port: int
    username: str
    password: SecretStr
    name: str

    @property
    def sqlalchemy_url(self) -> URL:
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.username,
            password=self.password.get_secret_value(),
            host=self.host,
            port=self.port,
            database=self.name,
        )


class Settings(BaseSettings):
    warning_letters: WarningLettersRetrieverConfig
    database: DatabaseConfig
    fda_ingestion: FDAIngestionConfig

    model_config = SettingsConfigDict(
        yaml_file="config.yml",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )