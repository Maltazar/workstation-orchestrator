from models.shared_main import SharedMain


class MacModel(SharedMain):
    pass

    def execute(self):
        """Execute mac-specific operations"""
        import modules.os.mac as mac_module

        mac_module.run_mac(self)
