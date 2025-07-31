#!/bin/bash
METHODS_LOADED=true

BOLD_UNDERLINE='\033[1;4m'

# Standard Colors
SD_RED='\033[1;31m'
SD_GREEN='\033[1;32m'
SD_YELLOW='\033[1;33m'
SD_BLUE='\033[1;34m'
SD_PURPLE='\033[1;35m'
SD_CYAN='\033[1;36m'
SD_WHITE='\033[1;37m'

# Reset
NC='\033[0m' # Reset colors

# Log Levels
ERROR="${BOLD_UNDERLINE}${SD_RED}ERROR${NC}${SD_RED}:${NC}"
WARNING="${BOLD_UNDERLINE}${SD_YELLOW}WARNING${NC}${SD_YELLOW}:${NC}"
INFO="${BOLD_UNDERLINE}INFO${NC}:"
DEBUG="${BOLD_UNDERLINE}${SD_PURPLE}DEBUG${NC}${SD_PURPLE}:${NC}"
FUNCTION_LOG="${SD_BLUE}FUNCTION:${NC}"

info_log() {
  echo -e "${INFO} $1" >&2
}

error_log() {
  echo -e "${ERROR} $1" >&2
}

warning_log() {
  echo -e "${WARNING} $1" >&2
}

debug_log() {
  if [[ $DEBUG_LOG == true ]]; then
    echo -e "${DEBUG} $1" >&2
  fi
}

# Function to display a yes/no popup
yes_no_popup() {
    if [ ! -z "$NO_POPUP" ]; then
        info_log "Skipping popup for $1"
        return 0
    fi

    while true; do
        read -p "$1 (y/n): " yn
        case $yn in
            [Yy]* ) return 0;;
            [Nn]* ) return 1;;
            * ) warning_log "Please answer yes or no.";;
        esac
    done
}

# Function to validate the OS type
validate_os_type() {
    if [ "$(uname)" == "Darwin" ]; then
        info_log "macOS"
    elif [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
        info_log "Linux"
    else
        error_log "Unsupported OS"
        exit 1
    fi
    info_log "continuing..."
}

# Function to install Homebrew on macOS
install_homebrew() {
    if ! command -v brew &> /dev/null; then
        if yes_no_popup "Homebrew is not installed. Would you like to install it?"; then
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            if [ $? -eq 0 ]; then
                info_log "Homebrew has been installed successfully."
            else
                error_log "Failed to install Homebrew."
                return 1
            fi
        else
            error_log "Homebrew installation aborted."
            return 1
        fi
    else
        debug_log "Homebrew is already installed."
    fi
}


# Function to install Python using Homebrew on macOS
install_python_brew() {
    if ! command -v brew &> /dev/null; then
        install_homebrew
    fi

    if yes_no_popup "Python3 is not installed. Would you like to install it using Homebrew?"; then
        brew install python@3.12
        if [ $? -eq 0 ]; then
            info_log "Python3 has been installed successfully."
        else
            error_log "Failed to install Python3."
            exit 1
        fi
    else
        error_log "Python3 installation aborted."
        exit 1
    fi
}

# Validate if venv module is available
validate_venv() {
    if ! python3 -c "import venv" &> /dev/null; then
        error_log "Python venv module is not available"
        if [ "$(uname)" == "Darwin" ]; then
            error_log "Try: brew install python"
        elif [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
            error_log "Try: sudo apt-get install python3-venv"
        fi
        exit 1
    fi
    debug_log "Python venv module is available"
}

# Setup and activate virtual environment
setup_venv() {
    local VENV_DIR=".venv"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "$VENV_DIR" ]; then
        info_log "Creating virtual environment..."
        python3 -m venv $VENV_DIR
        if [ $? -ne 0 ]; then
            error_log "Failed to create virtual environment"
            exit 1
        fi
        info_log "Virtual environment created successfully"
    fi

    # Activate virtual environment
    info_log "Activating virtual environment..."
    source $VENV_DIR/bin/activate
    if [ $? -ne 0 ]; then
        error_log "Failed to activate virtual environment"
        exit 1
    fi
    info_log "Virtual environment activated"
}

install_uv() {
    if ! command -v uv &> /dev/null; then
        info_log "Installing uv"
        curl -LsSf https://astral.sh/uv/install.sh | sh
        if [ $? -ne 0 ]; then
            error_log "Failed to install uv"
            exit 1
        fi
        info_log "uv has been installed successfully."
    else
        debug_log "uv is already installed."
    fi
}

# Function to install Python requirements in virtual environment
install_python_requirements() {
    if ! command -v uv &> /dev/null; then
        if yes_no_popup "uv is not installed. Would you like to install it?"; then
            install_uv
            info_log "Active venv is using uv"
            uv venv
            source .venv/bin/activate
            uv sync
        else
            info_log "Skipping uv installation, using pip directly."
            # Ensure we're in a virtual environment
            if [ -z "$VIRTUAL_ENV" ]; then
                setup_venv
            fi
            
            python3 -m pip install --upgrade pip
            python3 -m pip install -r $1
            if [ $? -eq 0 ]; then
                info_log "Python requirements have been installed successfully."
            else
                error_log "Failed to install Python requirements."
                exit 1
            fi
        fi
    else
        info_log "Active venv is using uv"
        uv venv
        source .venv/bin/activate
        uv sync
    fi
}

# Validate if Python is installed
validate_python() {
    if ! command -v python3 &> /dev/null; then
        echo "Python3 could not be found. Please install Python3 and try again."
        install_python_brew
    fi

    debug_log "Python3 is installed"
    validate_venv
    setup_venv
}

deactivate_venv() {
    deactivate
}