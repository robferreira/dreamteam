from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_AGENTS_BUNDLE_DIR = ROOT_DIR / "agents"
WORKFLOWS_DIR = ROOT_DIR / "workflows"
CONFIG_DIR = ROOT_DIR / "config"
PROJECTS_DIR = ROOT_DIR / "projects"
MEMORY_DIR = ROOT_DIR / "memory"


def get_agents_bundle_dir() -> Path:
    from src.settings import get_settings

    return get_settings().agents_bundle_dir.resolve()


def get_agents_dir() -> Path:
    return get_agents_bundle_dir()


def get_agents_default_dir() -> Path:
    return get_agents_bundle_dir() / "default"


def get_agents_custom_dir() -> Path:
    return get_agents_bundle_dir() / "custom"


def get_agents_skills_dir() -> Path:
    return get_agents_bundle_dir() / "skills"


def get_agents_instructions_dir() -> Path:
    return get_agents_bundle_dir() / "instructions"


def get_agents_plugins_dir() -> Path:
    return get_agents_bundle_dir() / "plugins"


def ensure_plugins_path() -> None:
    """Adiciona o bundle dir ao sys.path para importar o pacote plugins/."""
    import sys

    bundle = get_agents_bundle_dir()
    path_str = str(bundle)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
