import sys
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent.parent / "src" / "workstation_orchestrator"
sys.path.append(str(src_path))
