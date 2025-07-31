from models.shared_main import SharedMain


class LinuxModel(SharedMain):
    pass

    def execute(self):
        """Execute linux-specific operations"""
        import modules.os.linux as linux_module

        linux_module.run_linux(self)
