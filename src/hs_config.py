import json
from abc import ABCMeta, abstractmethod
from configparser import ConfigParser
from pathlib import Path
from typing import Any, Dict, Tuple, Type

import yaml
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class CustomSettingsSource(PydanticBaseSettingsSource):
    """
    自定义的配置文件来源基类
    """

    def __init__(
        self,
        settings_cls: type[BaseSettings],
        path: Path,
    ):
        super().__init__(settings_cls)
        self.path = path
        encoding = self.config.get("env_file_encoding")
        self.file_content = path.read_text(encoding)
        self.file_content_dict = self.get_file_dict()

    def __call__(self) -> dict[str, Any]:
        d: Dict[str, Any] = {}

        for field_name, field in self.settings_cls.model_fields.items():
            field_value, field_key, value_is_complex = self.get_field_value(field, field_name)
            if field_value is not None:
                d[field_key] = field_value

        return d

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(path={self.path!r})"

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        field_value = self.file_content_dict.get(field_name)
        return field_value, field_name, False

    @abstractmethod
    def get_file_dict(self) -> dict:
        """
        将配置文件读取成字典，子类自行实现
        Returns:

        """
        pass


class JsonSettingsSource(CustomSettingsSource):
    """
    json文件来源导入配置项
    """

    def get_file_dict(self):
        return json.loads(self.file_content)


class IniSettingsSource(CustomSettingsSource):
    """
    ini文件来源导入配置项
    """

    def get_file_dict(self):
        parser = ConfigParser()
        parser.read_string(self.file_content)
        return getattr(parser, "_sections", {}).get("settings", {})


class YamlSettingsSource(CustomSettingsSource):
    """
    Yaml文件来源导入配置项
    """

    def get_file_dict(self):
        return yaml.safe_load(self.file_content)


class ConfigBase(BaseSettings, metaclass=ABCMeta):
    """
    项目设置的基类
    """

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        env_file=(Path.cwd() / "configs").absolute() / ".env",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        """
        自定义配置来源
        Args:
            settings_cls:
            init_settings: 初始化设置
            env_settings:环境变量设置
            dotenv_settings:
            file_secret_settings:加密文件设置

        Returns:

        """
        # 默认的设置
        default_settings = {
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        }
        root_dir = (Path.cwd() / "configs").absolute()

        # json 配置文件
        json_file = root_dir / "settings.json"
        if json_file.exists():
            json_settings_source = JsonSettingsSource(settings_cls, json_file)
            default_settings.add(json_settings_source)

        # ini配置文件
        ini_file = root_dir / "settings.ini"
        if ini_file.exists():
            ini_settings_source = IniSettingsSource(settings_cls, ini_file)
            default_settings.add(ini_settings_source)

        # yaml配置文件
        yaml_file = root_dir / "settings.yaml"
        if yaml_file.exists():
            yaml_settings_source = YamlSettingsSource(settings_cls, yaml_file)
            default_settings.add(yaml_settings_source)

        return tuple(default_settings)
