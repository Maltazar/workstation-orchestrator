from typing import Optional
from pydantic import model_validator
from models.base_model import BaseConfigModel


class InstallItem(BaseConfigModel):
    name: str
    args: Optional[str] = None

    @model_validator(mode="before")
    def set_default_key(cls, values):
        if isinstance(values, str):
            return {"name": values}
        return values

    def run(self):
        import modules.install.install as install_module

        install_module.run_install(self)
