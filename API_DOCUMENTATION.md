# 📚 LazyScan API Documentation

## Overview

This document provides comprehensive API documentation for LazyScan's enhanced architecture, including the new cross-platform capabilities, intelligent cache analysis, plugin system, and performance optimizations.

---

## 🏗️ Core Architecture

### Platform Management

#### `PlatformManager`

Abstract base class for platform-specific implementations.

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class PlatformInfo:
    """Platform information container"""
    name: str
    version: str
    architecture: str
    supported_features: List[str]

class PlatformManager(ABC):
    """Abstract platform manager for cross-platform operations"""
    
    @abstractmethod
    def get_platform_info(self) -> PlatformInfo:
        """Get detailed platform information"""
        pass
    
    @abstractmethod
    def get_cache_directories(self) -> List[str]:
        """Get platform-specific cache directories"""
        pass
    
    @abstractmethod
    def get_temp_directories(self) -> List[str]:
        """Get platform-specific temporary directories"""
        pass
    
    @abstractmethod
    def is_safe_to_delete(self, path: str) -> bool:
        """Check if path is safe to delete on this platform"""
        pass
```

**Usage Example:**
```python
from core.platform import get_platform_manager

# Get platform-specific manager
platform = get_platform_manager()

# Get platform information
info = platform.get_platform_info()
print(f"Running on {info.name} {info.version}")

# Get cache directories
cache_dirs = platform.get_cache_directories()
for directory in cache_dirs:
    print(f"Cache directory: {directory}")
```

#### Platform-Specific Implementations

##### `MacOSPlatform`

```python
class MacOSPlatform(PlatformManager):
    """macOS-specific platform implementation"""
    
    def get_platform_info(self) -> PlatformInfo:
        """Get macOS platform information"""
        return PlatformInfo(
            name="macOS",
            version=platform.mac_ver()[0],
            architecture=platform.machine(),
            supported_features=[
                "spotlight_integration",
                "keychain_access",
                "app_sandbox_detection",
                "system_integrity_protection"
            ]
        )
    
    def get_cache_directories(self) -> List[str]:
        """Get macOS cache directories"""
        home = os.path.expanduser("~")
        return [
            f"{home}/Library/Caches",
            "/Library/Caches",
            "/System/Library/Caches",
            f"{home}/Library/Logs",
            "/var/log"
        ]
```

##### `WindowsPlatform`

```python
class WindowsPlatform(PlatformManager):
    """Windows-specific platform implementation"""
    
    def get_platform_info(self) -> PlatformInfo:
        """Get Windows platform information"""
        return PlatformInfo(
            name="Windows",
            version=platform.win32_ver()[0],
            architecture=platform.machine(),
            supported_features=[
                "registry_access",
                "wmi_integration",
                "windows_defender_integration",
                "uac_detection"
            ]
        )
    
    def get_cache_directories(self) -> List[str]:
        """Get Windows cache directories"""
        appdata = os.environ.get('APPDATA', '')
        localappdata = os.environ.get('LOCALAPPDATA', '')
        temp = os.environ.get('TEMP', '')
        
        return [
            f"{localappdata}\\Temp",
            f"{appdata}\\Local\\Temp",
            temp,
            f"{localappdata}\\Microsoft\\Windows\\INetCache",
            f"{localappdata}\\Google\\Chrome\\User Data\\Default\\Cache"
        ]
```

---

## 🧠 Intelligent Cache Analysis

### `CacheAnalyzer`

Advanced cache analysis engine with ML-ready architecture.

```python
from enum import Enum
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import hashlib
import time

class SafetyLevel(Enum):
    """Safety levels for cache deletion"""
    SAFE = "safe"
    CAUTION = "caution"
    DANGEROUS = "dangerous"
    UNKNOWN = "unknown"

class RecommendationAction(Enum):
    """Recommended actions for cache files"""
    DELETE = "delete"
    ARCHIVE = "archive"
    KEEP = "keep"
    REVIEW = "review"

@dataclass
class AnalysisResult:
    """Result of cache analysis"""
    path: str
    safety_level: SafetyLevel
    confidence_score: float  # 0.0 to 1.0
    recommended_action: RecommendationAction
    reasoning: List[str]
    estimated_impact: Dict[str, float]
    metadata: Dict[str, any]

class CacheAnalyzer:
    """Intelligent cache analysis engine"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.risk_threshold = self.config.get('risk_threshold', 0.7)
        self.confidence_threshold = self.config.get('confidence_threshold', 0.8)
        
        # Initialize analysis models
        self._load_analysis_models()
    
    def analyze_cache_path(self, cache_path: 'CachePath') -> AnalysisResult:
        """Analyze a single cache path for safety and recommendations"""
        
        # Step 1: Basic safety analysis
        safety_score = self._calculate_safety_score(cache_path)
        
        # Step 2: Usage pattern analysis
        usage_patterns = self._analyze_usage_patterns(cache_path)
        
        # Step 3: Risk assessment
        risk_assessment = self._assess_deletion_risk(cache_path, usage_patterns)
        
        # Step 4: Generate recommendation
        recommendation = self._generate_recommendation(
            safety_score, usage_patterns, risk_assessment
        )
        
        return AnalysisResult(
            path=cache_path.path,
            safety_level=self._determine_safety_level(safety_score),
            confidence_score=recommendation['confidence'],
            recommended_action=recommendation['action'],
            reasoning=recommendation['reasoning'],
            estimated_impact=risk_assessment,
            metadata={
                'safety_score': safety_score,
                'usage_patterns': usage_patterns,
                'analysis_timestamp': time.time()
            }
        )
    
    def batch_analyze(self, cache_paths: List['CachePath'], 
                     parallel: bool = True) -> List[AnalysisResult]:
        """Analyze multiple cache paths efficiently"""
        
        if parallel and len(cache_paths) > 10:
            return self._parallel_batch_analyze(cache_paths)
        else:
            return [self.analyze_cache_path(path) for path in cache_paths]
```

**Usage Example:**
```python
from core.analysis import CacheAnalyzer
from core.models import CachePath

# Initialize analyzer
analyzer = CacheAnalyzer({
    'risk_threshold': 0.6,
    'confidence_threshold': 0.75
})

# Analyze single cache path
cache_path = CachePath(
    path="/Users/user/Library/Caches/com.example.app/cache.db",
    application="Example App",
    cache_type="user"
)

result = analyzer.analyze_cache_path(cache_path)

print(f"Safety Level: {result.safety_level.value}")
print(f"Confidence: {result.confidence_score:.2f}")
print(f"Recommendation: {result.recommended_action.value}")
print(f"Reasoning: {', '.join(result.reasoning)}")
```

---

## 🔌 Plugin Architecture

### Plugin System Overview

The plugin system allows extending LazyScan with custom cache handlers, analyzers, and integrations.

#### `PluginInterface`

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

@dataclass
class PluginMetadata:
    """Plugin metadata container"""
    name: str
    version: str
    author: str
    description: str
    supported_platforms: List[str]
    dependencies: List[str]
    plugin_type: str

class PluginInterface(ABC):
    """Base interface for all LazyScan plugins"""
    
    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Get plugin metadata"""
        pass
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the plugin with configuration"""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Cleanup plugin resources"""
        pass
```

#### Plugin Types

##### `CacheHandlerPlugin`

```python
class CacheHandlerPlugin(PluginInterface):
    """Plugin for handling application-specific cache discovery"""
    
    @abstractmethod
    def get_supported_applications(self) -> List[str]:
        """Get list of supported applications"""
        pass
    
    @abstractmethod
    def get_cache_paths(self, application: str) -> List['CachePath']:
        """Get cache paths for specific application"""
        pass
    
    @abstractmethod
    def analyze_cache(self, cache_path: 'CachePath') -> 'AnalysisResult':
        """Analyze application-specific cache"""
        pass
```

##### `AnalyzerPlugin`

```python
class AnalyzerPlugin(PluginInterface):
    """Plugin for custom analysis algorithms"""
    
    @abstractmethod
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze individual file"""
        pass
    
    @abstractmethod
    def get_analysis_priority(self) -> int:
        """Get analysis priority (higher = more important)"""
        pass
```

#### `PluginManager`

```python
class PluginManager:
    """Manages plugin lifecycle and operations"""
    
    def __init__(self, plugin_directory: str = "plugins"):
        self.plugin_directory = plugin_directory
        self.loaded_plugins: Dict[str, PluginInterface] = {}
        self.plugin_registry: Dict[str, List[PluginInterface]] = {
            'cache_handlers': [],
            'analyzers': [],
            'exporters': [],
            'integrations': []
        }
    
    def load_plugins_from_directory(self, directory: str) -> List[str]:
        """Load all plugins from directory"""
        loaded_plugins = []
        
        for plugin_file in self.discover_plugins(directory):
            try:
                plugin_name = self.load_plugin(plugin_file)
                if plugin_name:
                    loaded_plugins.append(plugin_name)
            except Exception as e:
                print(f"Failed to load plugin {plugin_file}: {e}")
        
        return loaded_plugins
    
    def get_cache_handlers(self) -> List[CacheHandlerPlugin]:
        """Get all loaded cache handler plugins"""
        return self.plugin_registry.get('cache_handlers', [])
    
    def get_analyzers(self) -> List[AnalyzerPlugin]:
        """Get all loaded analyzer plugins"""
        return self.plugin_registry.get('analyzers', [])
```

**Plugin Development Example:**
```python
# plugins/chrome_cache_plugin.py
from core.plugins import CacheHandlerPlugin, PluginMetadata
from core.models import CachePath, AnalysisResult
from typing import List
import os

class ChromeCachePlugin(CacheHandlerPlugin):
    """Chrome-specific cache handler plugin"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name='chrome_cache_handler',
            version='1.0.0',
            author='LazyScan Team',
            description='Handles Google Chrome cache discovery and analysis',
            supported_platforms=['darwin', 'linux', 'win32'],
            dependencies=['psutil'],
            plugin_type='cache_handler'
        )
    
    def initialize(self, config) -> bool:
        self.chrome_paths = self._discover_chrome_installations()
        return len(self.chrome_paths) > 0
    
    def cleanup(self) -> None:
        pass
    
    def get_supported_applications(self) -> List[str]:
        return ['Google Chrome', 'Chromium']
    
    def get_cache_paths(self, application: str) -> List[CachePath]:
        cache_paths = []
        
        for chrome_path in self.chrome_paths:
            cache_dir = os.path.join(chrome_path, 'Default', 'Cache')
            if os.path.exists(cache_dir):
                cache_paths.append(CachePath(
                    path=cache_dir,
                    application=application,
                    cache_type='browser'
                ))
        
        return cache_paths
```

---

## ⚡ Performance Optimization

### `ScanOptimizer`

High-performance scanning with intelligent resource management.

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Callable, Dict, Any
from dataclasses import dataclass
import threading
import time

@dataclass
class ScanResult:
    """Result of directory scanning operation"""
    path: str
    total_files: int
    total_size: int
    scan_time: float
    error_count: int
    cache_paths: List['CachePath']

class ScanOptimizer:
    """Advanced scanning optimizations"""
    
    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) + 4)
        self.scan_cache: Dict[str, tuple] = {}  # path -> (timestamp, result)
        self.cache_ttl = 3600  # 1 hour cache TTL
    
    def parallel_scan(self, directories: List[str], 
                     progress_callback: Optional[Callable[[str, float], None]] = None) -> ScanResult:
        """Multi-threaded directory scanning with optimal thread allocation"""
        
        optimal_threads = self._calculate_optimal_threads(len(directories))
        
        with ThreadPoolExecutor(max_workers=optimal_threads) as executor:
            # Submit scanning tasks
            future_to_dir = {
                executor.submit(self._scan_directory_worker, directory): directory 
                for directory in directories
            }
            
            # Process results as they complete
            total_files = 0
            total_size = 0
            all_cache_paths = []
            error_count = 0
            completed = 0
            
            for future in as_completed(future_to_dir):
                directory = future_to_dir[future]
                
                try:
                    dir_result = future.result()
                    total_files += dir_result['file_count']
                    total_size += dir_result['total_size']
                    all_cache_paths.extend(dir_result['cache_paths'])
                    
                except Exception as e:
                    print(f"Error scanning directory {directory}: {e}")
                    error_count += 1
                
                completed += 1
                if progress_callback:
                    progress = completed / len(directories)
                    progress_callback(directory, progress)
        
        return ScanResult(
            path="multiple_directories",
            total_files=total_files,
            total_size=total_size,
            scan_time=time.time() - start_time,
            error_count=error_count,
            cache_paths=all_cache_paths
        )
```

**Usage Example:**
```python
from core.performance import ScanOptimizer

# Initialize optimizer
optimizer = ScanOptimizer(max_workers=8)

# Define progress callback
def progress_callback(directory: str, progress: float):
    print(f"Scanning {directory}: {progress:.1%} complete")

# Perform optimized scan
directories = [
    "/Users/user/Library/Caches",
    "/Users/user/Downloads",
    "/Users/user/Documents"
]

result = optimizer.parallel_scan(directories, progress_callback)

print(f"Scanned {result.total_files} files in {result.scan_time:.2f} seconds")
print(f"Total size: {result.total_size / (1024**3):.2f} GB")
print(f"Found {len(result.cache_paths)} cache files")
```

---

## 🔧 Configuration Management

### Configuration Schema

```python
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

@dataclass
class SecurityConfig:
    """Security configuration settings"""
    enable_audit_logging: bool = True
    require_confirmation: bool = True
    safe_mode: bool = True
    backup_before_delete: bool = True
    max_file_size_mb: int = 1000
    excluded_paths: List[str] = field(default_factory=list)

@dataclass
class PerformanceConfig:
    """Performance configuration settings"""
    max_workers: Optional[int] = None
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600
    memory_limit_mb: int = 1000
    enable_parallel_analysis: bool = True

@dataclass
class PluginConfig:
    """Plugin configuration settings"""
    plugin_directory: str = "plugins"
    auto_load_plugins: bool = True
    enabled_plugins: List[str] = field(default_factory=list)
    disabled_plugins: List[str] = field(default_factory=list)

@dataclass
class LazyScanConfig:
    """Main LazyScan configuration"""
    security: SecurityConfig = field(default_factory=SecurityConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    plugins: PluginConfig = field(default_factory=PluginConfig)
    
    # Application-specific settings
    supported_applications: List[str] = field(default_factory=lambda: [
        'Chrome', 'Firefox', 'Safari', 'Unity', 'Unreal Engine',
        'VS Code', 'Slack', 'Discord', 'Spotify'
    ])
    
    # Output settings
    output_format: str = "table"  # table, json, csv
    show_progress: bool = True
    verbose_logging: bool = False
```

### Configuration Loading

```python
import json
import yaml
from pathlib import Path
from typing import Union

class ConfigManager:
    """Manages LazyScan configuration"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._get_default_config_path()
        self.config = LazyScanConfig()
    
    def load_config(self, config_path: Optional[str] = None) -> LazyScanConfig:
        """Load configuration from file"""
        path = config_path or self.config_path
        
        if not os.path.exists(path):
            return self._create_default_config()
        
        try:
            with open(path, 'r') as f:
                if path.endswith('.json'):
                    config_data = json.load(f)
                elif path.endswith(('.yml', '.yaml')):
                    config_data = yaml.safe_load(f)
                else:
                    raise ValueError(f"Unsupported config format: {path}")
            
            return self._parse_config_data(config_data)
            
        except Exception as e:
            print(f"Error loading config from {path}: {e}")
            return self._create_default_config()
    
    def save_config(self, config: LazyScanConfig, config_path: Optional[str] = None) -> bool:
        """Save configuration to file"""
        path = config_path or self.config_path
        
        try:
            config_data = self._serialize_config(config)
            
            with open(path, 'w') as f:
                if path.endswith('.json'):
                    json.dump(config_data, f, indent=2)
                elif path.endswith(('.yml', '.yaml')):
                    yaml.dump(config_data, f, default_flow_style=False)
            
            return True
            
        except Exception as e:
            print(f"Error saving config to {path}: {e}")
            return False
```

**Usage Example:**
```python
from core.config import ConfigManager, LazyScanConfig, SecurityConfig

# Load configuration
config_manager = ConfigManager()
config = config_manager.load_config()

# Modify security settings
config.security.safe_mode = True
config.security.backup_before_delete = True
config.security.max_file_size_mb = 500

# Save updated configuration
config_manager.save_config(config)

# Use configuration in application
from core.lazyscan import OptimizedLazyScan

lazy_scan = OptimizedLazyScan(config=config)
result = lazy_scan.scan_with_optimization(["/path/to/scan"])
```

---

## 🔍 Error Handling and Logging

### Error Types

```python
class LazyScanError(Exception):
    """Base exception for LazyScan errors"""
    pass

class SecurityError(LazyScanError):
    """Security-related errors"""
    pass

class PluginError(LazyScanError):
    """Plugin-related errors"""
    pass

class PerformanceError(LazyScanError):
    """Performance-related errors"""
    pass

class ConfigurationError(LazyScanError):
    """Configuration-related errors"""
    pass
```

### Logging Configuration

```python
import logging
from typing import Optional

class LazyScanLogger:
    """Centralized logging for LazyScan"""
    
    def __init__(self, name: str = "lazyscan", level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup logging handlers"""
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # File handler
        file_handler = logging.FileHandler('lazyscan.log')
        file_handler.setLevel(logging.DEBUG)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        self.logger.error(message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.logger.debug(message, **kwargs)
```

---

## 🧪 Testing Framework

### Test Utilities

```python
import tempfile
import os
import shutil
from typing import List, Dict, Any
from unittest.mock import Mock, patch

class LazyScanTestCase:
    """Base test case for LazyScan tests"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_files = []
    
    def teardown_method(self):
        """Cleanup test environment"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_file(self, path: str, content: str = "test content") -> str:
        """Create a test file with content"""
        full_path = os.path.join(self.temp_dir, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'w') as f:
            f.write(content)
        
        self.test_files.append(full_path)
        return full_path
    
    def create_test_cache_structure(self) -> Dict[str, List[str]]:
        """Create a realistic cache directory structure"""
        cache_structure = {
            'chrome': [
                'Cache/data_0',
                'Cache/data_1',
                'Cache/index'
            ],
            'firefox': [
                'cache2/entries/file1.cache',
                'cache2/entries/file2.cache'
            ],
            'unity': [
                'cache/project1/Library/metadata',
                'cache/project1/Library/artifacts'
            ]
        }
        
        created_files = {}
        for app, files in cache_structure.items():
            created_files[app] = []
            for file_path in files:
                full_path = self.create_test_file(f"{app}/{file_path}")
                created_files[app].append(full_path)
        
        return created_files
```

---

## 📊 Metrics and Monitoring

### Performance Metrics

```python
from dataclasses import dataclass
from typing import Dict, List, Optional
import time

@dataclass
class PerformanceMetrics:
    """Performance metrics container"""
    operation_name: str
    start_time: float
    end_time: float
    files_processed: int
    bytes_processed: int
    errors_encountered: int
    memory_peak_mb: float
    
    @property
    def duration_seconds(self) -> float:
        return self.end_time - self.start_time
    
    @property
    def files_per_second(self) -> float:
        return self.files_processed / max(self.duration_seconds, 0.001)
    
    @property
    def bytes_per_second(self) -> float:
        return self.bytes_processed / max(self.duration_seconds, 0.001)

class MetricsCollector:
    """Collects and manages performance metrics"""
    
    def __init__(self):
        self.metrics_history: List[PerformanceMetrics] = []
        self.active_operations: Dict[str, float] = {}
    
    def start_operation(self, operation_name: str) -> str:
        """Start tracking an operation"""
        operation_id = f"{operation_name}_{int(time.time() * 1000)}"
        self.active_operations[operation_id] = time.time()
        return operation_id
    
    def end_operation(self, operation_id: str, 
                     files_processed: int = 0,
                     bytes_processed: int = 0,
                     errors_encountered: int = 0) -> PerformanceMetrics:
        """End tracking an operation and record metrics"""
        
        if operation_id not in self.active_operations:
            raise ValueError(f"Operation {operation_id} not found")
        
        start_time = self.active_operations.pop(operation_id)
        end_time = time.time()
        
        # Get memory usage
        try:
            import psutil
            memory_mb = psutil.Process().memory_info().rss / (1024 * 1024)
        except ImportError:
            memory_mb = 0.0
        
        metrics = PerformanceMetrics(
            operation_name=operation_id.split('_')[0],
            start_time=start_time,
            end_time=end_time,
            files_processed=files_processed,
            bytes_processed=bytes_processed,
            errors_encountered=errors_encountered,
            memory_peak_mb=memory_mb
        )
        
        self.metrics_history.append(metrics)
        return metrics
    
    def get_summary_stats(self, operation_name: Optional[str] = None) -> Dict[str, Any]:
        """Get summary statistics for operations"""
        
        relevant_metrics = self.metrics_history
        if operation_name:
            relevant_metrics = [
                m for m in self.metrics_history 
                if m.operation_name == operation_name
            ]
        
        if not relevant_metrics:
            return {}
        
        total_operations = len(relevant_metrics)
        total_files = sum(m.files_processed for m in relevant_metrics)
        total_bytes = sum(m.bytes_processed for m in relevant_metrics)
        total_duration = sum(m.duration_seconds for m in relevant_metrics)
        total_errors = sum(m.errors_encountered for m in relevant_metrics)
        
        avg_duration = total_duration / total_operations
        avg_files_per_sec = sum(m.files_per_second for m in relevant_metrics) / total_operations
        avg_memory = sum(m.memory_peak_mb for m in relevant_metrics) / total_operations
        
        return {
            'total_operations': total_operations,
            'total_files_processed': total_files,
            'total_bytes_processed': total_bytes,
            'total_duration_seconds': total_duration,
            'total_errors': total_errors,
            'average_duration_seconds': avg_duration,
            'average_files_per_second': avg_files_per_sec,
            'average_memory_usage_mb': avg_memory,
            'error_rate': total_errors / max(total_operations, 1)
        }
```

**Usage Example:**
```python
from core.metrics import MetricsCollector

# Initialize metrics collector
metrics = MetricsCollector()

# Track an operation
operation_id = metrics.start_operation("directory_scan")

# ... perform scanning operation ...

# End operation and record metrics
result_metrics = metrics.end_operation(
    operation_id,
    files_processed=1500,
    bytes_processed=1024*1024*500,  # 500MB
    errors_encountered=2
)

print(f"Scan completed in {result_metrics.duration_seconds:.2f} seconds")
print(f"Processed {result_metrics.files_per_second:.0f} files/second")

# Get summary statistics
summary = metrics.get_summary_stats("directory_scan")
print(f"Average scan time: {summary['average_duration_seconds']:.2f} seconds")
print(f"Error rate: {summary['error_rate']:.2%}")
```

---

## 🔄 Async Directory Scanning

### `scan_directory`

High-performance asynchronous directory scanning with progress callbacks and concurrency control.

```python
from pathlib import Path
from lazyscan.core.scan import scan_directory, scan_directory_sync

# Async scanning (recommended)
async def scan_with_progress():
    """Scan directory asynchronously with progress updates"""

    def progress_callback(path: Path, data: dict):
        """Progress callback receives scan status updates"""
        if 'files_processed' in data:
            print(f"Scanning {path.name}: {data['files_processed']} files")
        elif 'total_size' in data:
            print(f"Scan complete: {data['file_count']} files, {data['total_size']} bytes")

    result = await scan_directory(
        Path("/home/user/projects"),
        max_depth=3,                    # Limit directory depth
        exclude_patterns=["*.tmp", "*.log"],  # Exclude patterns
        progress_callback=progress_callback,
        concurrency_limit=10           # Concurrent operations
    )

    return result

# Synchronous wrapper (for backward compatibility)
def scan_legacy_style():
    """Synchronous scanning with deprecation warning"""
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)

        result = scan_directory_sync(
            Path("/home/user/projects"),
            max_depth=2,
            exclude_patterns=["node_modules"]
        )

    return result
```

#### Parameters

- `path` (Path): Root directory to scan
- `max_depth` (Optional[int]): Maximum directory depth (None = unlimited)
- `exclude_patterns` (Optional[List[str]]): Glob patterns to exclude
- `progress_callback` (Optional[Callable]): Progress update callback
- `concurrency_limit` (int): Maximum concurrent filesystem operations

#### Return Value

```python
{
    'total_size': int,      # Total bytes of all files
    'file_count': int,      # Number of files found
    'dir_count': int,       # Number of directories found
    'files': List[Tuple[str, int]],  # [(path, size), ...]
    'errors': List[Tuple[str, str]]  # [(path, error), ...]
}
```

#### AsyncProgressEmitter

Manages progress callbacks with intelligent batching to prevent UI flooding.

```python
from lazyscan.core.scan import AsyncProgressEmitter

# Custom progress emitter
emitter = AsyncProgressEmitter(
    callback=my_progress_callback,
    batch_interval=0.2  # Batch updates every 200ms
)

# Manual progress emission
await emitter.emit(Path("/some/dir"), {"status": "processing"})

# Cleanup (automatically called by scan_directory)
await emitter.shutdown()
```

### Migration Guide

#### From Synchronous to Asynchronous Scanning

**Before (v0.4.x):**
```python
from lazyscan.core.scanner import scan_directory_with_progress

# Blocking synchronous scan
file_sizes = scan_directory_with_progress(scan_path, colors)
```

**After (v0.5.x):**
```python
from lazyscan.core.scan import scan_directory

# Non-blocking async scan
result = await scan_directory(Path(scan_path), progress_callback=progress_func)
file_sizes = result['files']
```

#### Backward Compatibility

The synchronous `scan_directory_with_progress` function remains available but is deprecated. Use `scan_directory_sync` for new code requiring synchronous behavior:

```python
# New synchronous wrapper (recommended)
from lazyscan.core.scan import scan_directory_sync

result = scan_directory_sync(Path(scan_path))
files = result['files']  # Same format as before
```

### Performance Benefits

- **Concurrent I/O**: Multiple directories scanned simultaneously
- **Non-blocking UI**: Progress updates don't freeze the interface
- **Resource efficiency**: Controlled concurrency prevents system overload
- **Scalability**: Handles large directory trees efficiently

This comprehensive API documentation provides developers with all the necessary information to effectively use, extend, and integrate with LazyScan's enhanced architecture. The examples demonstrate real-world usage patterns and best practices for each component of the system.