#!/usr/bin/env python3
"""
Plugin system for LazyScan.
Provides extensible architecture for app-specific integrations.
"""

import importlib
from typing import Dict, List, Optional, Protocol, Any, Awaitable
from abc import ABC, abstractmethod

from ..core.logging_config import get_logger

logger = get_logger(__name__)


class PluginInterface(Protocol):
    """Protocol defining the interface all plugins must implement."""

    @property
    def name(self) -> str:
        """Plugin name."""
        ...

    @property
    def description(self) -> str:
        """Plugin description."""
        ...

    def scan(self, **kwargs) -> Dict[str, Any]:
        """Perform plugin-specific scanning."""
        ...

    def clean(self, **kwargs) -> Dict[str, Any]:
        """Perform plugin-specific cleaning."""
        ...

    async def scan_async(self, **kwargs) -> Dict[str, Any]:
        """Perform plugin-specific scanning asynchronously."""
        ...

    async def clean_async(self, **kwargs) -> Dict[str, Any]:
        """Perform plugin-specific cleaning asynchronously."""
        ...


class BasePlugin(ABC):
    """Base class for LazyScan plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Plugin description."""
        pass

    @abstractmethod
    def scan(self, **kwargs) -> Dict[str, Any]:
        """Perform plugin-specific scanning."""
        pass

    @abstractmethod
    def clean(self, **kwargs) -> Dict[str, Any]:
        """Perform plugin-specific cleaning."""
        pass

    @abstractmethod
    async def scan_async(self, **kwargs) -> Dict[str, Any]:
        """Perform plugin-specific scanning asynchronously."""
        pass

    @abstractmethod
    async def clean_async(self, **kwargs) -> Dict[str, Any]:
        """Perform plugin-specific cleaning asynchronously."""
        pass


class PluginManager:
    """Manages plugin discovery, loading, and execution."""

    def __init__(self):
        self._plugins: Dict[str, PluginInterface] = {}
        self._loaded = False

    @property
    def plugins(self) -> Dict[str, PluginInterface]:
        """Public access to loaded plugins."""
        if not self._loaded:
            self.load_plugins()
        return self._plugins

    def load_plugins(self) -> None:
        """Load all available plugins."""
        if self._loaded:
            return

        logger.info("Loading LazyScan plugins")

        # TODO: Add entry point loading for external plugins
        # For now, focus on built-in plugins

        # Load built-in plugins
        self._load_builtin_plugins()

        self._loaded = True
        logger.info(f"Plugin loading complete. Loaded {len(self._plugins)} plugins")

    def _load_builtin_plugins(self) -> None:
        """Load built-in plugins that are part of the core distribution."""
        builtin_plugins = [
            ('unity', 'lazyscan.apps.unity:UnityPlugin'),
            ('unreal', 'lazyscan.apps.unreal:UnrealPlugin'),
            ('chrome', 'lazyscan.apps.chrome:ChromePlugin'),
            ('firefox', 'lazyscan.apps.firefox:FirefoxPlugin'),
            ('vscode', 'lazyscan.apps.vscode:VSCodePlugin'),
        ]

        for plugin_name, module_path in builtin_plugins:
            try:
                module_name, class_name = module_path.split(':')
                module = importlib.import_module(module_name)
                plugin_class = getattr(module, class_name)
                plugin_instance = plugin_class()

                self._plugins[plugin_name] = plugin_instance
                logger.debug(f"Loaded built-in plugin: {plugin_name}")

            except (ImportError, AttributeError) as e:
                logger.debug(f"Built-in plugin {plugin_name} not available: {e}")
            except Exception as e:
                logger.warning(f"Failed to load built-in plugin {plugin_name}: {e}")

    def get_plugin(self, name: str) -> Optional[PluginInterface]:
        """Get a plugin by name."""
        if not self._loaded:
            self.load_plugins()
        return self._plugins.get(name)

    def list_plugins(self) -> List[str]:
        """List all available plugin names."""
        if not self._loaded:
            self.load_plugins()
        return list(self._plugins.keys())

    def get_plugin_info(self, name: str) -> Optional[Dict[str, str]]:
        """Get information about a specific plugin."""
        plugin = self.get_plugin(name)
        if plugin:
            return {
                'name': plugin.name,
                'description': plugin.description,
            }
        return None

    def scan_with_plugin(self, plugin_name: str, **kwargs) -> Dict[str, Any]:
        """Execute scan operation with a specific plugin."""
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            raise ValueError(f"Plugin '{plugin_name}' not found")

        logger.info(f"Executing scan with plugin: {plugin_name}")
        return plugin.scan(**kwargs)

    def clean_with_plugin(self, plugin_name: str, **kwargs) -> Dict[str, Any]:
        """Execute clean operation with a specific plugin."""
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            raise ValueError(f"Plugin '{plugin_name}' not found")

        logger.info(f"Executing clean with plugin: {plugin_name}")
        return plugin.clean(**kwargs)

    async def scan_with_plugin_async(self, plugin_name: str, **kwargs) -> Dict[str, Any]:
        """Execute async scan operation with a specific plugin."""
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            raise ValueError(f"Plugin '{plugin_name}' not found")

        logger.info(f"Executing async scan with plugin: {plugin_name}")
        return await plugin.scan_async(**kwargs)

    async def clean_with_plugin_async(self, plugin_name: str, **kwargs) -> Dict[str, Any]:
        """Execute async clean operation with a specific plugin."""
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            raise ValueError(f"Plugin '{plugin_name}' not found")

        logger.info(f"Executing async clean with plugin: {plugin_name}")
        return await plugin.clean_async(**kwargs)


# Global plugin manager instance
_plugin_manager = None


def get_plugin_manager() -> PluginManager:
    """Get the global plugin manager instance."""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager


def scan_with_plugin(plugin_name: str, **kwargs) -> Dict[str, Any]:
    """Convenience function to scan with a plugin."""
    return get_plugin_manager().scan_with_plugin(plugin_name, **kwargs)


def clean_with_plugin(plugin_name: str, **kwargs) -> Dict[str, Any]:
    """Convenience function to clean with a plugin."""
    return get_plugin_manager().clean_with_plugin(plugin_name, **kwargs)


async def scan_with_plugin_async(plugin_name: str, **kwargs) -> Dict[str, Any]:
    """Convenience function to scan with a plugin asynchronously."""
    return await get_plugin_manager().scan_with_plugin_async(plugin_name, **kwargs)


async def clean_with_plugin_async(plugin_name: str, **kwargs) -> Dict[str, Any]:
    """Convenience function to clean with a plugin asynchronously."""
    return await get_plugin_manager().clean_with_plugin_async(plugin_name, **kwargs)