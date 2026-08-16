from pathlib import Path

from pydantic import (
    BaseModel,
    Field,
    SecretStr,
)
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


class InspectionClassificationModelConfig(
    BaseModel
):
    dataset_version: str = Field(
        min_length=1,
    )
    model_version: str = Field(
        min_length=1,
    )
    artifact_root: Path
    random_state: int = 42
    maximum_iterations: int = Field(
        default=2000,
        gt=0,
    )


class ModelingConfig(BaseModel):
    inspection_classification: (
        InspectionClassificationModelConfig
    )


class Settings(BaseSettings):
    warning_letters: WarningLettersRetrieverConfig
    database: DatabaseConfig
    fda_ingestion: FDAIngestionConfig
    modeling: ModelingConfig

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
