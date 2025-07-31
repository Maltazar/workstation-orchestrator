from typing import List, Optional

from pydantic import model_validator, Field
from models.shared import SharedModel
from models.base_model import BaseConfigModel


class VSCodeSettings(BaseConfigModel):
    file: Optional[str]
    content: Optional[str]


class VSCodeExtensions(BaseConfigModel):
    install: List[str]
    uninstall: List[str] = Field(default=[])
    bin_file: Optional[str] = "code"

    @model_validator(mode="before")
    def set_default_key(cls, values):
        if hasattr(cls, "bin_file") and cls.bin_file is None:
            cls.bin_file = "code"
        if isinstance(values, str):
            return {"install": [f"{cls.bin_file} --install-extension {values}"]}
        if isinstance(values, list):
            return {
                "install": [
                    f"{cls.bin_file} --install-extension {item}" for item in values
                ]
            }
        return values

    @model_validator(mode="after")
    def validate_uninstall(self):
        if self.uninstall:
            self.install = [
                f"{self.bin_file} --uninstall-extension {item}"
                for item in self.uninstall
            ]
        return self


class VSCode(SharedModel):
    settings: Optional[VSCodeSettings]
    extensions: Optional[VSCodeExtensions]

    def execute(self):
        """Execute vscode-specific operations"""
        import modules.configure.vscode as vscode_module

        vscode_module.run_vscode(self)
