# 🔧 LazyScan Technical Implementation Guide

> **Engineering Excellence Framework**  
> Version: 1.0 | Target: Development Team | Focus: Clean Architecture & Best Practices

---

## 🏗️ Architecture Principles

### Core Design Philosophy
- **Security by Design**: Every component integrates with the security framework
- **Platform Agnostic**: Abstract platform-specific operations behind clean interfaces
- **Testable Code**: 90%+ test coverage with comprehensive unit and integration tests
- **Performance First**: Optimize for speed and memory efficiency
- **Extensible Design**: Plugin architecture for community contributions

### Clean Architecture Implementation

```
Domain Layer (Business Logic)
├── entities/          # Core business objects
├── use_cases/         # Application business rules
└── interfaces/        # Abstract interfaces

Application Layer (Orchestration)
├── services/          # Application services
├── handlers/          # Command/Query handlers
└── dto/              # Data transfer objects

Infrastructure Layer (External Concerns)
├── repositories/      # Data persistence
├── external_services/ # Third-party integrations
└── platform/         # Platform-specific implementations

Presentation Layer (User Interface)
├── cli/              # Command-line interface
├── web/              # Web dashboard
└── api/              # REST API endpoints
```

---

## 🚀 Cross-Platform Implementation

### Platform Abstraction Layer

```python
# core/platform_manager.py
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict, Optional
from dataclasses import dataclass
import platform
import os

class PlatformType(Enum):
    MACOS = "darwin"
    WINDOWS = "win32"
    LINUX = "linux"

@dataclass
class CachePath:
    """Represents a cache location with metadata"""
    path: str
    application: str
    cache_type: str  # 'user', 'system', 'temp'
    estimated_size: Optional[int] = None
    last_accessed: Optional[float] = None
    safety_level: str = 'unknown'  # 'safe', 'caution', 'dangerous'

class PlatformInterface(ABC):
    """Abstract interface for platform-specific operations"""
    
    @abstractmethod
    def get_cache_directories(self) -> List[str]:
        """Get platform-specific cache directories"""
        pass
    
    @abstractmethod
    def get_temp_directories(self) -> List[str]:
        """Get platform-specific temporary directories"""
        pass
    
    @abstractmethod
    def get_application_cache_path(self, app_name: str) -> Optional[str]:
        """Get cache path for specific application"""
        pass
    
    @abstractmethod
    def get_user_data_directory(self) -> str:
        """Get user data directory for storing app data"""
        pass
    
    @abstractmethod
    def is_path_safe_to_delete(self, path: str) -> bool:
        """Platform-specific safety check for path deletion"""
        pass

class MacOSPlatform(PlatformInterface):
    """macOS-specific implementation"""
    
    def get_cache_directories(self) -> List[str]:
        home = os.path.expanduser("~")
        return [
            f"{home}/Library/Caches",
            f"{home}/Library/Application Support",
            "/Library/Caches",
            "/System/Library/Caches"
        ]
    
    def get_temp_directories(self) -> List[str]:
        return [
            "/tmp",
            "/var/tmp",
            os.path.expanduser("~/Library/Caches/TemporaryItems")
        ]
    
    def get_application_cache_path(self, app_name: str) -> Optional[str]:
        """Get macOS application cache path"""
        cache_mappings = {
            'chrome': 'Google/Chrome',
            'firefox': 'Firefox',
            'safari': 'com.apple.Safari',
            'vscode': 'com.microsoft.VSCode',
            'discord': 'com.hnc.Discord',
            'slack': 'com.tinyspeck.slackmacgap',
            'spotify': 'com.spotify.client',
            'zoom': 'us.zoom.xos'
        }
        
        if app_name.lower() in cache_mappings:
            home = os.path.expanduser("~")
            return f"{home}/Library/Caches/{cache_mappings[app_name.lower()]}"
        return None
    
    def get_user_data_directory(self) -> str:
        return os.path.expanduser("~/Library/Application Support/LazyScan")
    
    def is_path_safe_to_delete(self, path: str) -> bool:
        """macOS-specific safety checks"""
        dangerous_paths = {
            '/System', '/Library/System', '/usr/lib', '/usr/bin',
            '/Applications', '/Library/Application Support/Apple'
        }
        return not any(path.startswith(dangerous) for dangerous in dangerous_paths)

class WindowsPlatform(PlatformInterface):
    """Windows-specific implementation"""
    
    def get_cache_directories(self) -> List[str]:
        appdata = os.environ.get('APPDATA', '')
        localappdata = os.environ.get('LOCALAPPDATA', '')
        return [
            f"{localappdata}\\Temp",
            f"{appdata}\\Microsoft\\Windows\\Recent",
            f"{localappdata}\\Microsoft\\Windows\\INetCache",
            "C:\\Windows\\Temp"
        ]
    
    def get_temp_directories(self) -> List[str]:
        temp = os.environ.get('TEMP', 'C:\\Windows\\Temp')
        tmp = os.environ.get('TMP', temp)
        return [temp, tmp, "C:\\Windows\\Temp"]
    
    def get_application_cache_path(self, app_name: str) -> Optional[str]:
        """Get Windows application cache path"""
        localappdata = os.environ.get('LOCALAPPDATA', '')
        appdata = os.environ.get('APPDATA', '')
        
        cache_mappings = {
            'chrome': f"{localappdata}\\Google\\Chrome\\User Data\\Default\\Cache",
            'firefox': f"{localappdata}\\Mozilla\\Firefox\\Profiles",
            'edge': f"{localappdata}\\Microsoft\\Edge\\User Data\\Default\\Cache",
            'vscode': f"{appdata}\\Code\\CachedData",
            'discord': f"{appdata}\\discord\\Cache",
            'slack': f"{appdata}\\Slack\\Cache",
            'spotify': f"{appdata}\\Spotify\\Storage",
            'zoom': f"{appdata}\\Zoom\\data"
        }
        
        return cache_mappings.get(app_name.lower())
    
    def get_user_data_directory(self) -> str:
        appdata = os.environ.get('APPDATA', '')
        return f"{appdata}\\LazyScan"
    
    def is_path_safe_to_delete(self, path: str) -> bool:
        """Windows-specific safety checks"""
        dangerous_paths = {
            'C:\\Windows', 'C:\\Program Files', 'C:\\Program Files (x86)',
            'C:\\System Volume Information', 'C:\\$Recycle.Bin'
        }
        return not any(path.upper().startswith(dangerous.upper()) for dangerous in dangerous_paths)

class LinuxPlatform(PlatformInterface):
    """Linux-specific implementation"""
    
    def get_cache_directories(self) -> List[str]:
        home = os.path.expanduser("~")
        return [
            f"{home}/.cache",
            f"{home}/.local/share",
            "/tmp",
            "/var/tmp",
            "/var/cache"
        ]
    
    def get_temp_directories(self) -> List[str]:
        return ["/tmp", "/var/tmp", "/dev/shm"]
    
    def get_application_cache_path(self, app_name: str) -> Optional[str]:
        """Get Linux application cache path"""
        home = os.path.expanduser("~")
        
        cache_mappings = {
            'chrome': f"{home}/.cache/google-chrome",
            'firefox': f"{home}/.cache/mozilla/firefox",
            'vscode': f"{home}/.cache/vscode",
            'discord': f"{home}/.config/discord/Cache",
            'slack': f"{home}/.config/Slack/Cache",
            'spotify': f"{home}/.cache/spotify"
        }
        
        return cache_mappings.get(app_name.lower())
    
    def get_user_data_directory(self) -> str:
        home = os.path.expanduser("~")
        return f"{home}/.local/share/lazyscan"
    
    def is_path_safe_to_delete(self, path: str) -> bool:
        """Linux-specific safety checks"""
        dangerous_paths = {
            '/bin', '/sbin', '/usr/bin', '/usr/sbin', '/lib', '/usr/lib',
            '/etc', '/boot', '/sys', '/proc', '/dev'
        }
        return not any(path.startswith(dangerous) for dangerous in dangerous_paths)

class PlatformManager:
    """Main platform management class"""
    
    def __init__(self):
        self.platform_type = self._detect_platform()
        self.platform_impl = self._create_platform_implementation()
    
    def _detect_platform(self) -> PlatformType:
        """Detect current platform"""
        system = platform.system().lower()
        if system == 'darwin':
            return PlatformType.MACOS
        elif system == 'windows':
            return PlatformType.WINDOWS
        elif system == 'linux':
            return PlatformType.LINUX
        else:
            raise UnsupportedPlatformError(f"Unsupported platform: {system}")
    
    def _create_platform_implementation(self) -> PlatformInterface:
        """Factory method for platform implementations"""
        implementations = {
            PlatformType.MACOS: MacOSPlatform,
            PlatformType.WINDOWS: WindowsPlatform,
            PlatformType.LINUX: LinuxPlatform
        }
        return implementations[self.platform_type]()
    
    def get_all_cache_paths(self) -> List[CachePath]:
        """Get all cache paths for current platform"""
        cache_paths = []
        
        # System cache directories
        for cache_dir in self.platform_impl.get_cache_directories():
            if os.path.exists(cache_dir):
                cache_paths.append(CachePath(
                    path=cache_dir,
                    application='system',
                    cache_type='system'
                ))
        
        # Application-specific caches
        applications = ['chrome', 'firefox', 'vscode', 'discord', 'slack', 'spotify']
        for app in applications:
            app_cache = self.platform_impl.get_application_cache_path(app)
            if app_cache and os.path.exists(app_cache):
                cache_paths.append(CachePath(
                    path=app_cache,
                    application=app,
                    cache_type='user'
                ))
        
        return cache_paths
    
    def is_safe_to_delete(self, path: str) -> bool:
        """Check if path is safe to delete on current platform"""
        return self.platform_impl.is_path_safe_to_delete(path)

class UnsupportedPlatformError(Exception):
    """Raised when platform is not supported"""
    pass
```

---

## 🧠 Intelligent Cache Analysis

### Analysis Engine Implementation

```python
# core/intelligence_engine.py
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from enum import Enum
import os
import time
import hashlib
import json
from pathlib import Path

class SafetyLevel(Enum):
    SAFE = "safe"
    CAUTION = "caution"
    DANGEROUS = "dangerous"

class RecommendationAction(Enum):
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
    estimated_impact: Dict[str, any]
    metadata: Dict[str, any]

@dataclass
class FileAnalysis:
    """Individual file analysis result"""
    path: str
    size: int
    last_accessed: float
    last_modified: float
    file_type: str
    access_frequency: int
    importance_score: float

class CacheAnalyzer:
    """Intelligent cache analysis engine"""
    
    def __init__(self, user_data_dir: str):
        self.user_data_dir = user_data_dir
        self.analysis_history = self._load_analysis_history()
        self.user_preferences = self._load_user_preferences()
        
        # File type risk mappings
        self.file_type_risks = {
            '.tmp': 0.1,    # Very safe
            '.cache': 0.2,  # Safe
            '.log': 0.3,    # Generally safe
            '.db': 0.7,     # Caution
            '.plist': 0.8,  # macOS preferences - dangerous
            '.exe': 0.9,    # Executable - very dangerous
            '.dll': 0.9,    # Library - very dangerous
        }
        
        # Application criticality scores
        self.app_criticality = {
            'system': 0.9,      # System files - high risk
            'chrome': 0.3,      # Browser cache - low risk
            'firefox': 0.3,     # Browser cache - low risk
            'vscode': 0.4,      # IDE cache - low-medium risk
            'discord': 0.2,     # Chat app - very low risk
            'spotify': 0.2,     # Music app - very low risk
            'unity': 0.5,       # Game engine - medium risk
            'unreal': 0.5,      # Game engine - medium risk
        }
    
    def analyze_cache_path(self, cache_path: CachePath) -> AnalysisResult:
        """Perform comprehensive analysis of cache path"""
        reasoning = []
        risk_factors = []
        
        # 1. Application criticality analysis
        app_risk = self.app_criticality.get(cache_path.application, 0.5)
        risk_factors.append(('application_risk', app_risk))
        reasoning.append(f"Application '{cache_path.application}' has risk level {app_risk}")
        
        # 2. File system analysis
        if os.path.exists(cache_path.path):
            file_analysis = self._analyze_files_in_path(cache_path.path)
            file_risk = self._calculate_file_risk(file_analysis)
            risk_factors.append(('file_risk', file_risk))
            reasoning.append(f"File analysis indicates risk level {file_risk:.2f}")
            
            # 3. Usage pattern analysis
            usage_risk = self._analyze_usage_patterns(cache_path.path, file_analysis)
            risk_factors.append(('usage_risk', usage_risk))
            reasoning.append(f"Usage pattern analysis: risk level {usage_risk:.2f}")
            
            # 4. Size and impact analysis
            total_size = sum(f.size for f in file_analysis)
            size_impact = self._calculate_size_impact(total_size)
            reasoning.append(f"Total size: {self._format_size(total_size)} - Impact: {size_impact}")
        else:
            risk_factors.append(('file_risk', 0.0))
            risk_factors.append(('usage_risk', 0.0))
            reasoning.append("Path does not exist - no risk")
        
        # 5. Historical analysis
        historical_risk = self._analyze_historical_data(cache_path.path)
        risk_factors.append(('historical_risk', historical_risk))
        reasoning.append(f"Historical analysis: risk level {historical_risk:.2f}")
        
        # Calculate overall risk score
        overall_risk = self._calculate_weighted_risk(risk_factors)
        safety_level = self._determine_safety_level(overall_risk)
        recommended_action = self._determine_recommended_action(overall_risk, cache_path)
        confidence_score = self._calculate_confidence_score(risk_factors)
        
        return AnalysisResult(
            path=cache_path.path,
            safety_level=safety_level,
            confidence_score=confidence_score,
            recommended_action=recommended_action,
            reasoning=reasoning,
            estimated_impact={
                'risk_score': overall_risk,
                'size_impact': size_impact if 'size_impact' in locals() else 'unknown',
                'performance_impact': self._estimate_performance_impact(cache_path)
            },
            metadata={
                'analysis_timestamp': time.time(),
                'analyzer_version': '1.0',
                'risk_factors': dict(risk_factors)
            }
        )
    
    def _analyze_files_in_path(self, path: str) -> List[FileAnalysis]:
        """Analyze individual files in the given path"""
        file_analyses = []
        
        try:
            for root, dirs, files in os.walk(path):
                for file in files[:100]:  # Limit to first 100 files for performance
                    file_path = os.path.join(root, file)
                    try:
                        stat = os.stat(file_path)
                        file_ext = Path(file).suffix.lower()
                        
                        file_analyses.append(FileAnalysis(
                            path=file_path,
                            size=stat.st_size,
                            last_accessed=stat.st_atime,
                            last_modified=stat.st_mtime,
                            file_type=file_ext,
                            access_frequency=self._get_access_frequency(file_path),
                            importance_score=self._calculate_file_importance(file_path, stat)
                        ))
                    except (OSError, IOError):
                        continue  # Skip files we can't access
        except (OSError, IOError):
            pass  # Skip directories we can't access
        
        return file_analyses
    
    def _calculate_file_risk(self, file_analyses: List[FileAnalysis]) -> float:
        """Calculate risk based on file types and characteristics"""
        if not file_analyses:
            return 0.0
        
        total_risk = 0.0
        total_weight = 0.0
        
        for file_analysis in file_analyses:
            # Base risk from file type
            type_risk = self.file_type_risks.get(file_analysis.file_type, 0.5)
            
            # Adjust risk based on file characteristics
            if file_analysis.size > 100 * 1024 * 1024:  # Files > 100MB
                type_risk *= 1.2  # Slightly more risky
            
            # Recent files are slightly more risky to delete
            days_since_modified = (time.time() - file_analysis.last_modified) / (24 * 3600)
            if days_since_modified < 7:
                type_risk *= 1.1
            
            weight = file_analysis.size  # Weight by file size
            total_risk += type_risk * weight
            total_weight += weight
        
        return total_risk / total_weight if total_weight > 0 else 0.5
    
    def _analyze_usage_patterns(self, path: str, file_analyses: List[FileAnalysis]) -> float:
        """Analyze usage patterns to determine risk"""
        if not file_analyses:
            return 0.5
        
        current_time = time.time()
        recent_access_count = 0
        total_files = len(file_analyses)
        
        for file_analysis in file_analyses:
            # Check if file was accessed recently (within 30 days)
            days_since_access = (current_time - file_analysis.last_accessed) / (24 * 3600)
            if days_since_access < 30:
                recent_access_count += 1
        
        # Higher recent access ratio = higher risk to delete
        recent_access_ratio = recent_access_count / total_files
        
        # Convert to risk score (0.0 = safe to delete, 1.0 = dangerous to delete)
        return recent_access_ratio * 0.8  # Cap at 0.8 since cache files are generally safe
    
    def _calculate_size_impact(self, size_bytes: int) -> str:
        """Calculate the impact of deleting files of given size"""
        if size_bytes < 10 * 1024 * 1024:  # < 10MB
            return "minimal"
        elif size_bytes < 100 * 1024 * 1024:  # < 100MB
            return "low"
        elif size_bytes < 1024 * 1024 * 1024:  # < 1GB
            return "medium"
        else:
            return "high"
    
    def _analyze_historical_data(self, path: str) -> float:
        """Analyze historical cleanup data for this path"""
        path_hash = hashlib.md5(path.encode()).hexdigest()
        
        if path_hash in self.analysis_history:
            history = self.analysis_history[path_hash]
            
            # If we've successfully cleaned this path before, it's safer
            if history.get('successful_cleanups', 0) > 0:
                return max(0.1, history.get('last_risk_score', 0.5) * 0.8)
            
            # If there were issues, it's riskier
            if history.get('cleanup_issues', 0) > 0:
                return min(0.9, history.get('last_risk_score', 0.5) * 1.2)
        
        return 0.5  # Default risk for unknown paths
    
    def _calculate_weighted_risk(self, risk_factors: List[Tuple[str, float]]) -> float:
        """Calculate weighted overall risk score"""
        weights = {
            'application_risk': 0.3,
            'file_risk': 0.25,
            'usage_risk': 0.25,
            'historical_risk': 0.2
        }
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for factor_name, risk_value in risk_factors:
            weight = weights.get(factor_name, 0.1)
            weighted_sum += risk_value * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.5
    
    def _determine_safety_level(self, risk_score: float) -> SafetyLevel:
        """Determine safety level based on risk score"""
        if risk_score < 0.3:
            return SafetyLevel.SAFE
        elif risk_score < 0.7:
            return SafetyLevel.CAUTION
        else:
            return SafetyLevel.DANGEROUS
    
    def _determine_recommended_action(self, risk_score: float, cache_path: CachePath) -> RecommendationAction:
        """Determine recommended action based on analysis"""
        if risk_score < 0.2:
            return RecommendationAction.DELETE
        elif risk_score < 0.4:
            return RecommendationAction.ARCHIVE
        elif risk_score < 0.7:
            return RecommendationAction.REVIEW
        else:
            return RecommendationAction.KEEP
    
    def _calculate_confidence_score(self, risk_factors: List[Tuple[str, float]]) -> float:
        """Calculate confidence in the analysis"""
        # More risk factors analyzed = higher confidence
        factor_count = len(risk_factors)
        base_confidence = min(0.9, factor_count * 0.2)
        
        # Adjust based on data availability
        has_file_data = any(name == 'file_risk' and value > 0 for name, value in risk_factors)
        has_historical_data = any(name == 'historical_risk' and value != 0.5 for name, value in risk_factors)
        
        if has_file_data:
            base_confidence += 0.1
        if has_historical_data:
            base_confidence += 0.1
        
        return min(1.0, base_confidence)
    
    def _get_access_frequency(self, file_path: str) -> int:
        """Get access frequency for file (placeholder for future ML implementation)"""
        # This would be implemented with actual usage tracking
        return 0
    
    def _calculate_file_importance(self, file_path: str, stat) -> float:
        """Calculate importance score for individual file"""
        # Placeholder for more sophisticated importance calculation
        return 0.5
    
    def _estimate_performance_impact(self, cache_path: CachePath) -> str:
        """Estimate performance impact of cleanup"""
        if cache_path.application in ['chrome', 'firefox', 'safari']:
            return "Browser may need to rebuild cache - temporary slowdown"
        elif cache_path.application in ['unity', 'unreal']:
            return "Development tools may need to recompile - significant initial slowdown"
        else:
            return "Minimal performance impact expected"
    
    def _format_size(self, size_bytes: int) -> str:
        """Format size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    def _load_analysis_history(self) -> Dict:
        """Load historical analysis data"""
        history_file = os.path.join(self.user_data_dir, 'analysis_history.json')
        try:
            with open(history_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _load_user_preferences(self) -> Dict:
        """Load user preferences for analysis"""
        prefs_file = os.path.join(self.user_data_dir, 'analysis_preferences.json')
        try:
            with open(prefs_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                'risk_tolerance': 'medium',  # 'low', 'medium', 'high'
                'auto_delete_threshold': 0.2,
                'require_confirmation_threshold': 0.4
            }
    
    def save_analysis_result(self, result: AnalysisResult, cleanup_successful: bool = None):
        """Save analysis result for future reference"""
        path_hash = hashlib.md5(result.path.encode()).hexdigest()
        
        history_entry = {
            'last_analysis': time.time(),
            'last_risk_score': result.estimated_impact['risk_score'],
            'last_safety_level': result.safety_level.value,
            'analysis_count': self.analysis_history.get(path_hash, {}).get('analysis_count', 0) + 1
        }
        
        if cleanup_successful is not None:
            if cleanup_successful:
                history_entry['successful_cleanups'] = self.analysis_history.get(path_hash, {}).get('successful_cleanups', 0) + 1
            else:
                history_entry['cleanup_issues'] = self.analysis_history.get(path_hash, {}).get('cleanup_issues', 0) + 1
        
        self.analysis_history[path_hash] = history_entry
        
        # Save to disk
        history_file = os.path.join(self.user_data_dir, 'analysis_history.json')
        os.makedirs(self.user_data_dir, exist_ok=True)
        with open(history_file, 'w') as f:
            json.dump(self.analysis_history, f, indent=2)
```

---

## 🔌 Plugin Architecture

### Plugin System Implementation

```python
# core/plugin_manager.py
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Type, Any
from dataclasses import dataclass
import importlib.util
import inspect
import os
import json
from pathlib import Path

@dataclass
class PluginMetadata:
    """Plugin metadata information"""
    name: str
    version: str
    author: str
    description: str
    supported_platforms: List[str]
    dependencies: List[str]
    plugin_type: str  # 'cache_handler', 'analyzer', 'exporter', 'integration'

class PluginInterface(ABC):
    """Base interface for all plugins"""
    
    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata"""
        pass
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize plugin with configuration"""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Cleanup plugin resources"""
        pass

class CacheHandlerPlugin(PluginInterface):
    """Interface for cache handling plugins"""
    
    @abstractmethod
    def get_supported_applications(self) -> List[str]:
        """Return list of supported application names"""
        pass
    
    @abstractmethod
    def get_cache_paths(self, application: str) -> List[CachePath]:
        """Get cache paths for specified application"""
        pass
    
    @abstractmethod
    def analyze_cache(self, cache_path: CachePath) -> AnalysisResult:
        """Analyze cache for cleanup recommendations"""
        pass

class AnalyzerPlugin(PluginInterface):
    """Interface for file analysis plugins"""
    
    @abstractmethod
    def get_supported_file_types(self) -> List[str]:
        """Return list of supported file extensions"""
        pass
    
    @abstractmethod
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze individual file"""
        pass

class ExporterPlugin(PluginInterface):
    """Interface for export format plugins"""
    
    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """Return list of supported export formats"""
        pass
    
    @abstractmethod
    def export_results(self, results: List[AnalysisResult], output_path: str, format_type: str) -> bool:
        """Export analysis results to specified format"""
        pass

class IntegrationPlugin(PluginInterface):
    """Interface for external service integration plugins"""
    
    @abstractmethod
    def get_integration_type(self) -> str:
        """Return integration type (e.g., 'monitoring', 'cloud', 'notification')"""
        pass
    
    @abstractmethod
    def send_data(self, data: Dict[str, Any]) -> bool:
        """Send data to external service"""
        pass

class PluginManager:
    """Manages plugin loading, registration, and execution"""
    
    def __init__(self, plugin_directory: str):
        self.plugin_directory = plugin_directory
        self.loaded_plugins: Dict[str, PluginInterface] = {}
        self.plugin_registry: Dict[str, List[PluginInterface]] = {
            'cache_handler': [],
            'analyzer': [],
            'exporter': [],
            'integration': []
        }
        self.plugin_configs: Dict[str, Dict[str, Any]] = {}
        
        # Ensure plugin directory exists
        os.makedirs(plugin_directory, exist_ok=True)
    
    def discover_plugins(self) -> List[str]:
        """Discover available plugins in plugin directory"""
        plugin_files = []
        
        for root, dirs, files in os.walk(self.plugin_directory):
            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    plugin_files.append(os.path.join(root, file))
        
        return plugin_files
    
    def load_plugin(self, plugin_path: str) -> Optional[PluginInterface]:
        """Load a single plugin from file path"""
        try:
            # Load plugin module
            spec = importlib.util.spec_from_file_location("plugin_module", plugin_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Cannot load plugin spec from {plugin_path}")
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find plugin class
            plugin_class = self._find_plugin_class(module)
            if plugin_class is None:
                raise ValueError(f"No valid plugin class found in {plugin_path}")
            
            # Instantiate plugin
            plugin_instance = plugin_class()
            
            # Validate plugin
            if not self._validate_plugin(plugin_instance):
                raise ValueError(f"Plugin validation failed for {plugin_path}")
            
            # Get plugin metadata
            metadata = plugin_instance.get_metadata()
            
            # Load plugin configuration
            config = self._load_plugin_config(metadata.name)
            
            # Initialize plugin
            if not plugin_instance.initialize(config):
                raise RuntimeError(f"Plugin initialization failed for {metadata.name}")
            
            # Register plugin
            self.loaded_plugins[metadata.name] = plugin_instance
            self._register_plugin_by_type(plugin_instance, metadata.plugin_type)
            
            print(f"Successfully loaded plugin: {metadata.name} v{metadata.version}")
            return plugin_instance
            
        except Exception as e:
            print(f"Failed to load plugin from {plugin_path}: {str(e)}")
            return None
    
    def load_all_plugins(self) -> int:
        """Load all discovered plugins"""
        plugin_files = self.discover_plugins()
        loaded_count = 0
        
        for plugin_file in plugin_files:
            if self.load_plugin(plugin_file) is not None:
                loaded_count += 1
        
        print(f"Loaded {loaded_count} plugins from {len(plugin_files)} discovered")
        return loaded_count
    
    def get_plugins_by_type(self, plugin_type: str) -> List[PluginInterface]:
        """Get all plugins of specified type"""
        return self.plugin_registry.get(plugin_type, [])
    
    def get_cache_handlers(self) -> List[CacheHandlerPlugin]:
        """Get all cache handler plugins"""
        return [p for p in self.plugin_registry['cache_handler'] if isinstance(p, CacheHandlerPlugin)]
    
    def get_analyzers(self) -> List[AnalyzerPlugin]:
        """Get all analyzer plugins"""
        return [p for p in self.plugin_registry['analyzer'] if isinstance(p, AnalyzerPlugin)]
    
    def get_exporters(self) -> List[ExporterPlugin]:
        """Get all exporter plugins"""
        return [p for p in self.plugin_registry['exporter'] if isinstance(p, ExporterPlugin)]
    
    def get_integrations(self) -> List[IntegrationPlugin]:
        """Get all integration plugins"""
        return [p for p in self.plugin_registry['integration'] if isinstance(p, IntegrationPlugin)]
    
    def get_cache_paths_from_plugins(self, application: str) -> List[CachePath]:
        """Get cache paths for application from all relevant plugins"""
        cache_paths = []
        
        for handler in self.get_cache_handlers():
            if application in handler.get_supported_applications():
                try:
                    paths = handler.get_cache_paths(application)
                    cache_paths.extend(paths)
                except Exception as e:
                    print(f"Error getting cache paths from plugin {handler.get_metadata().name}: {e}")
        
        return cache_paths
    
    def analyze_with_plugins(self, cache_path: CachePath) -> List[AnalysisResult]:
        """Analyze cache path using all relevant plugins"""
        results = []
        
        # Try cache handler plugins first
        for handler in self.get_cache_handlers():
            if cache_path.application in handler.get_supported_applications():
                try:
                    result = handler.analyze_cache(cache_path)
                    results.append(result)
                except Exception as e:
                    print(f"Error analyzing with plugin {handler.get_metadata().name}: {e}")
        
        # Try analyzer plugins for file-level analysis
        for analyzer in self.get_analyzers():
            try:
                file_analysis = analyzer.analyze_file(cache_path.path)
                # Convert to AnalysisResult format if needed
                # This would need proper conversion logic
            except Exception as e:
                print(f"Error analyzing file with plugin {analyzer.get_metadata().name}: {e}")
        
        return results
    
    def export_with_plugins(self, results: List[AnalysisResult], output_path: str, format_type: str) -> bool:
        """Export results using appropriate plugin"""
        for exporter in self.get_exporters():
            if format_type in exporter.get_supported_formats():
                try:
                    return exporter.export_results(results, output_path, format_type)
                except Exception as e:
                    print(f"Error exporting with plugin {exporter.get_metadata().name}: {e}")
        
        return False
    
    def notify_integrations(self, event_type: str, data: Dict[str, Any]) -> None:
        """Notify integration plugins of events"""
        for integration in self.get_integrations():
            try:
                integration.send_data({
                    'event_type': event_type,
                    'timestamp': time.time(),
                    'data': data
                })
            except Exception as e:
                print(f"Error notifying integration {integration.get_metadata().name}: {e}")
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a specific plugin"""
        if plugin_name in self.loaded_plugins:
            plugin = self.loaded_plugins[plugin_name]
            
            try:
                plugin.cleanup()
                
                # Remove from registry
                for plugin_type, plugins in self.plugin_registry.items():
                    if plugin in plugins:
                        plugins.remove(plugin)
                
                # Remove from loaded plugins
                del self.loaded_plugins[plugin_name]
                
                print(f"Successfully unloaded plugin: {plugin_name}")
                return True
                
            except Exception as e:
                print(f"Error unloading plugin {plugin_name}: {e}")
                return False
        
        return False
    
    def unload_all_plugins(self) -> None:
        """Unload all plugins"""
        plugin_names = list(self.loaded_plugins.keys())
        for plugin_name in plugin_names:
            self.unload_plugin(plugin_name)
    
    def _find_plugin_class(self, module) -> Optional[Type[PluginInterface]]:
        """Find the plugin class in the module"""
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if (issubclass(obj, PluginInterface) and 
                obj != PluginInterface and 
                not inspect.isabstract(obj)):
                return obj
        return None
    
    def _validate_plugin(self, plugin: PluginInterface) -> bool:
        """Validate plugin implementation"""
        try:
            # Check if plugin implements required methods
            metadata = plugin.get_metadata()
            if not isinstance(metadata, PluginMetadata):
                return False
            
            # Additional validation based on plugin type
            if isinstance(plugin, CacheHandlerPlugin):
                apps = plugin.get_supported_applications()
                if not isinstance(apps, list):
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _register_plugin_by_type(self, plugin: PluginInterface, plugin_type: str) -> None:
        """Register plugin in appropriate registry"""
        if plugin_type in self.plugin_registry:
            self.plugin_registry[plugin_type].append(plugin)
    
    def _load_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """Load configuration for specific plugin"""
        config_file = os.path.join(self.plugin_directory, 'configs', f'{plugin_name}.json')
        
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}  # Return empty config if file doesn't exist or is invalid
    
    def get_plugin_info(self) -> Dict[str, Any]:
        """Get information about all loaded plugins"""
        info = {
            'total_plugins': len(self.loaded_plugins),
            'plugins_by_type': {k: len(v) for k, v in self.plugin_registry.items()},
            'loaded_plugins': []
        }
        
        for plugin_name, plugin in self.loaded_plugins.items():
            metadata = plugin.get_metadata()
            info['loaded_plugins'].append({
                'name': metadata.name,
                'version': metadata.version,
                'author': metadata.author,
                'type': metadata.plugin_type,
                'description': metadata.description
            })
        
        return info
```

---

## 🧪 Testing Framework

### Comprehensive Test Suite

```python
# tests/test_platform_manager.py
import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock
from core.platform_manager import (
    PlatformManager, PlatformType, CachePath,
    MacOSPlatform, WindowsPlatform, LinuxPlatform
)

class TestPlatformManager:
    """Test suite for PlatformManager"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Cleanup test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('platform.system')
    def test_platform_detection_macos(self, mock_system):
        """Test macOS platform detection"""
        mock_system.return_value = 'Darwin'
        manager = PlatformManager()
        assert manager.platform_type == PlatformType.MACOS
        assert isinstance(manager.platform_impl, MacOSPlatform)
    
    @patch('platform.system')
    def test_platform_detection_windows(self, mock_system):
        """Test Windows platform detection"""
        mock_system.return_value = 'Windows'
        manager = PlatformManager()
        assert manager.platform_type == PlatformType.WINDOWS
        assert isinstance(manager.platform_impl, WindowsPlatform)
    
    @patch('platform.system')
    def test_platform_detection_linux(self, mock_system):
        """Test Linux platform detection"""
        mock_system.return_value = 'Linux'
        manager = PlatformManager()
        assert manager.platform_type == PlatformType.LINUX
        assert isinstance(manager.platform_impl, LinuxPlatform)
    
    def test_macos_cache_directories(self):
        """Test macOS cache directory discovery"""
        platform = MacOSPlatform()
        cache_dirs = platform.get_cache_directories()
        
        assert any('Library/Caches' in path for path in cache_dirs)
        assert any('Library/Application Support' in path for path in cache_dirs)
    
    def test_windows_cache_directories(self):
        """Test Windows cache directory discovery"""
        with patch.dict(os.environ, {'APPDATA': 'C:\\Users\\Test\\AppData\\Roaming',
                                     'LOCALAPPDATA': 'C:\\Users\\Test\\AppData\\Local'}):
            platform = WindowsPlatform()
            cache_dirs = platform.get_cache_directories()
            
            assert any('AppData' in path for path in cache_dirs)
            assert any('Temp' in path for path in cache_dirs)
    
    def test_linux_cache_directories(self):
        """Test Linux cache directory discovery"""
        platform = LinuxPlatform()
        cache_dirs = platform.get_cache_directories()
        
        assert any('.cache' in path for path in cache_dirs)
        assert any('.local/share' in path for path in cache_dirs)
    
    def test_application_cache_mapping_chrome(self):
        """Test Chrome cache path mapping across platforms"""
        # macOS
        macos_platform = MacOSPlatform()
        macos_chrome = macos_platform.get_application_cache_path('chrome')
        assert 'Google/Chrome' in macos_chrome
        
        # Windows
        with patch.dict(os.environ, {'LOCALAPPDATA': 'C:\\Users\\Test\\AppData\\Local'}):
            windows_platform = WindowsPlatform()
            windows_chrome = windows_platform.get_application_cache_path('chrome')
            assert 'Google\\Chrome' in windows_chrome
        
        # Linux
        linux_platform = LinuxPlatform()
        linux_chrome = linux_platform.get_application_cache_path('chrome')
        assert 'google-chrome' in linux_chrome
    
    def test_safety_checks(self):
        """Test platform-specific safety checks"""
        # macOS safety checks
        macos_platform = MacOSPlatform()
        assert not macos_platform.is_path_safe_to_delete('/System/Library')
        assert not macos_platform.is_path_safe_to_delete('/Applications')
        assert macos_platform.is_path_safe_to_delete('/Users/test/Library/Caches/com.example.app')
        
        # Windows safety checks
        windows_platform = WindowsPlatform()
        assert not windows_platform.is_path_safe_to_delete('C:\\Windows')
        assert not windows_platform.is_path_safe_to_delete('C:\\Program Files')
        assert windows_platform.is_path_safe_to_delete('C:\\Users\\test\\AppData\\Local\\Temp')
        
        # Linux safety checks
        linux_platform = LinuxPlatform()
        assert not linux_platform.is_path_safe_to_delete('/bin')
        assert not linux_platform.is_path_safe_to_delete('/usr/lib')
        assert linux_platform.is_path_safe_to_delete('/home/test/.cache')
    
    @patch('os.path.exists')
    def test_get_all_cache_paths(self, mock_exists):
        """Test comprehensive cache path discovery"""
        mock_exists.return_value = True
        
        with patch('platform.system', return_value='Darwin'):
            manager = PlatformManager()
            cache_paths = manager.get_all_cache_paths()
            
            assert len(cache_paths) > 0
            assert all(isinstance(path, CachePath) for path in cache_paths)
            
            # Check for system caches
            system_caches = [p for p in cache_paths if p.application == 'system']
            assert len(system_caches) > 0
            
            # Check for application caches
            app_caches = [p for p in cache_paths if p.application != 'system']
            assert len(app_caches) > 0

# tests/test_intelligence_engine.py
import pytest
import tempfile
import os
import time
from unittest.mock import patch, MagicMock
from core.intelligence_engine import (
    CacheAnalyzer, AnalysisResult, SafetyLevel, 
    RecommendationAction, FileAnalysis
)
from core.platform_manager import CachePath

class TestIntelligenceEngine:
    """Test suite for Intelligence Engine"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.analyzer = CacheAnalyzer(self.temp_dir)
    
    def teardown_method(self):
        """Cleanup test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_analyzer_initialization(self):
        """Test analyzer initialization"""
        assert self.analyzer.user_data_dir == self.temp_dir
        assert isinstance(self.analyzer.file_type_risks, dict)
        assert isinstance(self.analyzer.app_criticality, dict)
    
    def test_safe_cache_analysis(self):
        """Test analysis of safe cache path"""
        cache_path = CachePath(
            path='/tmp/test_cache',
            application='chrome',
            cache_type='user'
        )
        
        with patch('os.path.exists', return_value=False):
            result = self.analyzer.analyze_cache_path(cache_path)
            
            assert isinstance(result, AnalysisResult)
            assert result.safety_level in [SafetyLevel.SAFE, SafetyLevel.CAUTION]
            assert result.confidence_score > 0.0
            assert len(result.reasoning) > 0
    
    def test_dangerous_cache_analysis(self):
        """Test analysis of dangerous cache path"""
        cache_path = CachePath(
            path='/System/Library/Critical',
            application='system',
            cache_type='system'
        )
        
        with patch('os.path.exists', return_value=True):
            with patch.object(self.analyzer, '_analyze_files_in_path', return_value=[]):
                result = self.analyzer.analyze_cache_path(cache_path)
                
                # System applications should have higher risk
                assert result.estimated_impact['risk_score'] > 0.5
    
    def test_file_analysis(self):
        """Test individual file analysis"""
        # Create test files
        test_file = os.path.join(self.temp_dir, 'test.tmp')
        with open(test_file, 'w') as f:
            f.write('test content')
        
        file_analyses = self.analyzer._analyze_files_in_path(self.temp_dir)
        
        assert len(file_analyses) > 0
        assert all(isinstance(fa, FileAnalysis) for fa in file_analyses)
        assert any(fa.file_type == '.tmp' for fa in file_analyses)
    
    def test_risk_calculation(self):
        """Test risk calculation logic"""
        file_analyses = [
            FileAnalysis(
                path='/test/file1.tmp',
                size=1024,
                last_accessed=time.time() - 86400,  # 1 day ago
                last_modified=time.time() - 86400,
                file_type='.tmp',
                access_frequency=0,
                importance_score=0.1
            ),
            FileAnalysis(
                path='/test/file2.exe',
                size=1024*1024,
                last_accessed=time.time() - 3600,  # 1 hour ago
                last_modified=time.time() - 3600,
                file_type='.exe',
                access_frequency=10,
                importance_score=0.9
            )
        ]
        
        risk_score = self.analyzer._calculate_file_risk(file_analyses)
        
        # Should be higher risk due to .exe file
        assert risk_score > 0.5
    
    def test_usage_pattern_analysis(self):
        """Test usage pattern analysis"""
        current_time = time.time()
        
        # Recent files (higher risk to delete)
        recent_files = [
            FileAnalysis(
                path='/test/recent.tmp',
                size=1024,
                last_accessed=current_time - 3600,  # 1 hour ago
                last_modified=current_time - 3600,
                file_type='.tmp',
                access_frequency=5,
                importance_score=0.3
            )
        ]
        
        # Old files (lower risk to delete)
        old_files = [
            FileAnalysis(
                path='/test/old.tmp',
                size=1024,
                last_accessed=current_time - 86400*60,  # 60 days ago
                last_modified=current_time - 86400*60,
                file_type='.tmp',
                access_frequency=0,
                importance_score=0.1
            )
        ]
        
        recent_risk = self.analyzer._analyze_usage_patterns('/test', recent_files)
        old_risk = self.analyzer._analyze_usage_patterns('/test', old_files)
        
        assert recent_risk > old_risk
    
    def test_safety_level_determination(self):
        """Test safety level determination"""
        assert self.analyzer._determine_safety_level(0.1) == SafetyLevel.SAFE
        assert self.analyzer._determine_safety_level(0.5) == SafetyLevel.CAUTION
        assert self.analyzer._determine_safety_level(0.8) == SafetyLevel.DANGEROUS
    
    def test_recommendation_action(self):
        """Test recommendation action determination"""
        cache_path = CachePath(path='/test', application='chrome', cache_type='user')
        
        assert self.analyzer._determine_recommended_action(0.1, cache_path) == RecommendationAction.DELETE
        assert self.analyzer._determine_recommended_action(0.3, cache_path) == RecommendationAction.ARCHIVE
        assert self.analyzer._determine_recommended_action(0.5, cache_path) == RecommendationAction.REVIEW
        assert self.analyzer._determine_recommended_action(0.8, cache_path) == RecommendationAction.KEEP
    
    def test_analysis_history_persistence(self):
        """Test analysis history saving and loading"""
        cache_path = CachePath(path='/test/cache', application='test', cache_type='user')
        
        with patch('os.path.exists', return_value=False):
            result = self.analyzer.analyze_cache_path(cache_path)
            self.analyzer.save_analysis_result(result, cleanup_successful=True)
        
        # Create new analyzer instance to test loading
        new_analyzer = CacheAnalyzer(self.temp_dir)
        
        # History should be loaded
        assert len(new_analyzer.analysis_history) > 0

# tests/test_plugin_manager.py
import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
from core.plugin_manager import (
    PluginManager, PluginMetadata, CacheHandlerPlugin,
    AnalyzerPlugin, ExporterPlugin, IntegrationPlugin
)

class MockCacheHandlerPlugin(CacheHandlerPlugin):
    """Mock cache handler plugin for testing"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name='mock_cache_handler',
            version='1.0.0',
            author='Test Author',
            description='Mock cache handler for testing',
            supported_platforms=['darwin', 'linux', 'win32'],
            dependencies=[],
            plugin_type='cache_handler'
        )
    
    def initialize(self, config) -> bool:
        return True
    
    def cleanup(self) -> None:
        pass
    
    def get_supported_applications(self) -> List[str]:
        return ['test_app']
    
    def get_cache_paths(self, application: str) -> List[CachePath]:
        return [CachePath(path='/test/cache', application=application, cache_type='user')]
    
    def analyze_cache(self, cache_path: CachePath) -> AnalysisResult:
        return AnalysisResult(
            path=cache_path.path,
            safety_level=SafetyLevel.SAFE,
            confidence_score=0.8,
            recommended_action=RecommendationAction.DELETE,
            reasoning=['Test analysis'],
            estimated_impact={'risk_score': 0.2},
            metadata={'test': True}
        )

class TestPluginManager:
    """Test suite for PluginManager"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.plugin_manager = PluginManager(self.temp_dir)
    
    def teardown_method(self):
        """Cleanup test environment"""
        self.plugin_manager.unload_all_plugins()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_plugin_manager_initialization(self):
        """Test plugin manager initialization"""
        assert self.plugin_manager.plugin_directory == self.temp_dir
        assert len(self.plugin_manager.loaded_plugins) == 0
        assert os.path.exists(self.temp_dir)
    
    def test_plugin_discovery(self):
        """Test plugin discovery"""
        # Create mock plugin file
        plugin_file = os.path.join(self.temp_dir, 'test_plugin.py')
        with open(plugin_file, 'w') as f:
            f.write('# Mock plugin file')
        
        discovered = self.plugin_manager.discover_plugins()
        assert plugin_file in discovered
    
    def test_plugin_loading_success(self):
        """Test successful plugin loading"""
        # This would require creating actual plugin files
        # For now, test the plugin registration directly
        mock_plugin = MockCacheHandlerPlugin()
        
        # Manually register for testing
        metadata = mock_plugin.get_metadata()
        self.plugin_manager.loaded_plugins[metadata.name] = mock_plugin
        self.plugin_manager._register_plugin_by_type(mock_plugin, metadata.plugin_type)
        
        assert len(self.plugin_manager.loaded_plugins) == 1
        assert len(self.plugin_manager.get_cache_handlers()) == 1
    
    def test_plugin_type_filtering(self):
        """Test plugin filtering by type"""
        mock_plugin = MockCacheHandlerPlugin()
        metadata = mock_plugin.get_metadata()
        
        self.plugin_manager.loaded_plugins[metadata.name] = mock_plugin
        self.plugin_manager._register_plugin_by_type(mock_plugin, metadata.plugin_type)
        
        cache_handlers = self.plugin_manager.get_cache_handlers()
        analyzers = self.plugin_manager.get_analyzers()
        
        assert len(cache_handlers) == 1
        assert len(analyzers) == 0
    
    def test_cache_path_retrieval_from_plugins(self):
        """Test cache path retrieval through plugins"""
        mock_plugin = MockCacheHandlerPlugin()
        metadata = mock_plugin.get_metadata()
        
        self.plugin_manager.loaded_plugins[metadata.name] = mock_plugin
        self.plugin_manager._register_plugin_by_type(mock_plugin, metadata.plugin_type)
        
        cache_paths = self.plugin_manager.get_cache_paths_from_plugins('test_app')
        
        assert len(cache_paths) == 1
        assert cache_paths[0].application == 'test_app'
    
    def test_plugin_unloading(self):
        """Test plugin unloading"""
        mock_plugin = MockCacheHandlerPlugin()
        metadata = mock_plugin.get_metadata()
        
        self.plugin_manager.loaded_plugins[metadata.name] = mock_plugin
        self.plugin_manager._register_plugin_by_type(mock_plugin, metadata.plugin_type)
        
        assert len(self.plugin_manager.loaded_plugins) == 1
        
        success = self.plugin_manager.unload_plugin(metadata.name)
        
        assert success
        assert len(self.plugin_manager.loaded_plugins) == 0
        assert len(self.plugin_manager.get_cache_handlers()) == 0

---

## 🚀 Performance Optimization

### Multi-threaded Scanning Implementation

```python
# core/performance_optimizer.py
import threading
import queue
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Iterator, Optional, Callable, Dict, Any
from dataclasses import dataclass
import os
import psutil
from pathlib import Path

@dataclass
class ScanResult:
    """Result of directory scanning operation"""
    path: str
    total_files: int
    total_size: int
    scan_time: float
    error_count: int
    cache_paths: List[CachePath]

@dataclass
class PerformanceMetrics:
    """Performance metrics for scanning operations"""
    start_time: float
    end_time: float
    total_files_scanned: int
    total_directories_scanned: int
    total_size_processed: int
    threads_used: int
    memory_peak_mb: float
    errors_encountered: int

class ScanOptimizer:
    """Advanced scanning optimizations for LazyScan"""
    
    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) + 4)
        self.scan_cache: Dict[str, tuple] = {}  # path -> (timestamp, result)
        self.cache_ttl = 3600  # 1 hour cache TTL
        
        # Performance monitoring
        self.performance_history: List[PerformanceMetrics] = []
    
    def parallel_scan(self, directories: List[str], 
                     progress_callback: Optional[Callable[[str, float], None]] = None) -> ScanResult:
        """Multi-threaded directory scanning with optimal thread allocation"""
        start_time = time.time()
        total_files = 0
        total_size = 0
        all_cache_paths = []
        error_count = 0
        
        # Calculate optimal thread count based on directory count and system resources
        optimal_threads = self._calculate_optimal_threads(len(directories))
        
        with ThreadPoolExecutor(max_workers=optimal_threads) as executor:
            # Submit scanning tasks
            future_to_dir = {
                executor.submit(self._scan_directory_worker, directory): directory 
                for directory in directories
            }
            
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
        
        scan_time = time.time() - start_time
        
        # Record performance metrics
        self._record_performance_metrics(
            start_time, time.time(), total_files, len(directories),
            total_size, optimal_threads, error_count
        )
        
        return ScanResult(
            path="multiple_directories",
            total_files=total_files,
            total_size=total_size,
            scan_time=scan_time,
            error_count=error_count,
            cache_paths=all_cache_paths
        )
    
    def _calculate_optimal_threads(self, directory_count: int) -> int:
        """Calculate optimal thread count based on system resources and workload"""
        cpu_count = os.cpu_count() or 1
        memory_gb = psutil.virtual_memory().total / (1024**3)
        
        # Base thread calculation
        base_threads = min(cpu_count * 2, directory_count)
        
        # Adjust based on available memory (1 thread per 2GB of RAM)
        memory_threads = int(memory_gb / 2)
        
        # Conservative approach for I/O bound operations
        optimal = min(base_threads, memory_threads, self.max_workers)
        
        return max(1, optimal)
    
    def _scan_directory_worker(self, directory: str) -> Dict[str, Any]:
        """Worker function for scanning individual directories"""
        file_count = 0
        total_size = 0
        cache_paths = []
        
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        stat_info = os.stat(file_path)
                        file_count += 1
                        total_size += stat_info.st_size
                        
                        # Check if this is a cache file
                        if self._is_cache_file(file_path):
                            cache_paths.append(CachePath(
                                path=file_path,
                                application=self._detect_application(file_path),
                                cache_type='user'
                            ))
                    except (OSError, IOError):
                        # Skip files we can't access
                        continue
        
        except Exception as e:
            print(f"Error walking directory {directory}: {e}")
        
        return {
            'file_count': file_count,
            'total_size': total_size,
            'cache_paths': cache_paths
        }
    
    def _is_cache_file(self, file_path: str) -> bool:
        """Determine if a file is likely a cache file"""
        cache_indicators = [
            'cache', 'temp', 'tmp', '.cache', 'Cache',
            'Caches', 'logs', 'log', '.log'
        ]
        
        path_lower = file_path.lower()
        return any(indicator in path_lower for indicator in cache_indicators)
    
    def _detect_application(self, file_path: str) -> str:
        """Detect which application a cache file belongs to"""
        path_parts = file_path.lower().split(os.sep)
        
        app_mappings = {
            'chrome': 'Google Chrome',
            'firefox': 'Mozilla Firefox',
            'safari': 'Safari',
            'unity': 'Unity',
            'unreal': 'Unreal Engine',
            'vscode': 'Visual Studio Code',
            'slack': 'Slack',
            'discord': 'Discord',
            'spotify': 'Spotify'
        }
        
        for part in path_parts:
            for key, app_name in app_mappings.items():
                if key in part:
                    return app_name
        
        return 'Unknown'
    
    def _record_performance_metrics(self, start_time: float, end_time: float,
                                  files_scanned: int, dirs_scanned: int,
                                  size_processed: int, threads_used: int,
                                  errors: int) -> None:
        """Record performance metrics for analysis"""
        memory_info = psutil.Process().memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)
        
        metrics = PerformanceMetrics(
            start_time=start_time,
            end_time=end_time,
            total_files_scanned=files_scanned,
            total_directories_scanned=dirs_scanned,
            total_size_processed=size_processed,
            threads_used=threads_used,
            memory_peak_mb=memory_mb,
            errors_encountered=errors
        )
        
        self.performance_history.append(metrics)
        
        # Keep only last 100 metrics to prevent memory bloat
        if len(self.performance_history) > 100:
            self.performance_history = self.performance_history[-100:]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics"""
        if not self.performance_history:
            return {}
        
        recent_metrics = self.performance_history[-10:]  # Last 10 scans
        
        avg_scan_time = sum(m.end_time - m.start_time for m in recent_metrics) / len(recent_metrics)
        avg_files_per_second = sum(m.total_files_scanned for m in recent_metrics) / sum(m.end_time - m.start_time for m in recent_metrics)
        avg_memory_usage = sum(m.memory_peak_mb for m in recent_metrics) / len(recent_metrics)
        
        return {
            'average_scan_time_seconds': round(avg_scan_time, 2),
            'average_files_per_second': round(avg_files_per_second, 2),
            'average_memory_usage_mb': round(avg_memory_usage, 2),
            'total_scans_performed': len(self.performance_history),
            'total_errors': sum(m.errors_encountered for m in self.performance_history)
        }

class OptimizedLazyScan:
    """Enhanced LazyScan with performance optimizations"""
    
    def __init__(self):
        self.optimizer = ScanOptimizer()
        self.cache_analyzer = CacheAnalyzer()
        self.plugin_manager = PluginManager()
        
        # Load performance-optimized plugins
        self.plugin_manager.load_plugins_from_directory('plugins/')
    
    def scan_with_optimization(self, directories: List[str], 
                             enable_analysis: bool = True,
                             progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Perform optimized scanning with intelligent analysis"""
        
        # Step 1: Parallel directory scanning
        scan_result = self.optimizer.parallel_scan(directories, progress_callback)
        
        # Step 2: Intelligent cache analysis (if enabled)
        analysis_results = []
        if enable_analysis and scan_result.cache_paths:
            analysis_results = self.cache_analyzer.batch_analyze(
                scan_result.cache_paths,
                parallel=True
            )
        
        # Step 3: Plugin-based enhancement
        plugin_results = []
        for plugin in self.plugin_manager.get_cache_handlers():
            try:
                plugin_paths = plugin.get_cache_paths('all')
                plugin_results.extend(plugin_paths)
            except Exception as e:
                print(f"Plugin error: {e}")
        
        # Step 4: Compile comprehensive results
        return {
            'scan_summary': {
                'total_files': scan_result.total_files,
                'total_size_bytes': scan_result.total_size,
                'scan_time_seconds': scan_result.scan_time,
                'directories_scanned': len(directories),
                'errors_encountered': scan_result.error_count
            },
            'cache_analysis': {
                'total_cache_files': len(scan_result.cache_paths),
                'analyzed_files': len(analysis_results),
                'safe_to_delete': len([r for r in analysis_results if r.recommended_action == RecommendationAction.DELETE]),
                'requires_caution': len([r for r in analysis_results if r.safety_level == SafetyLevel.CAUTION])
            },
            'plugin_enhancement': {
                'plugins_loaded': len(self.plugin_manager.loaded_plugins),
                'additional_paths_found': len(plugin_results)
            },
            'performance_metrics': self.optimizer.get_performance_summary(),
            'detailed_results': {
                'cache_paths': scan_result.cache_paths,
                'analysis_results': analysis_results,
                'plugin_paths': plugin_results
            }
        }
    
    def get_optimization_recommendations(self) -> List[str]:
        """Get performance optimization recommendations"""
        recommendations = []
        perf_summary = self.optimizer.get_performance_summary()
        
        if not perf_summary:
            return ['No performance data available yet. Run a scan first.']
        
        # Memory usage recommendations
        if perf_summary.get('average_memory_usage_mb', 0) > 1000:
            recommendations.append(
                'High memory usage detected. Consider reducing max_workers or scanning smaller directory sets.'
            )
        
        # Scan speed recommendations
        if perf_summary.get('average_files_per_second', 0) < 100:
            recommendations.append(
                'Slow scanning detected. Consider using SSD storage or reducing concurrent operations.'
            )
        
        # Error rate recommendations
        error_rate = perf_summary.get('total_errors', 0) / max(perf_summary.get('total_scans_performed', 1), 1)
        if error_rate > 0.1:
            recommendations.append(
                'High error rate detected. Check file permissions and disk health.'
            )
        
        if not recommendations:
            recommendations.append('Performance is optimal. No recommendations at this time.')
        
        return recommendations
```

---

## 🧪 Testing Strategy

### Comprehensive Test Suite

```python
# tests/test_performance_optimizer.py
import pytest
import tempfile
import os
import time
from unittest.mock import Mock, patch
from core.performance_optimizer import ScanOptimizer, OptimizedLazyScan

class TestScanOptimizer:
    """Test suite for ScanOptimizer"""
    
    def setup_method(self):
        """Setup test environment"""
        self.optimizer = ScanOptimizer(max_workers=2)
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Cleanup test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_optimal_thread_calculation(self):
        """Test optimal thread calculation"""
        # Test with small directory count
        threads = self.optimizer._calculate_optimal_threads(2)
        assert threads >= 1
        assert threads <= self.optimizer.max_workers
        
        # Test with large directory count
        threads = self.optimizer._calculate_optimal_threads(100)
        assert threads >= 1
        assert threads <= self.optimizer.max_workers
    
    def test_directory_worker(self):
        """Test directory scanning worker"""
        # Create test files
        test_file = os.path.join(self.temp_dir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('test content')
        
        result = self.optimizer._scan_directory_worker(self.temp_dir)
        
        assert result['file_count'] >= 1
        assert result['total_size'] > 0
        assert isinstance(result['cache_paths'], list)
    
    def test_cache_file_detection(self):
        """Test cache file detection logic"""
        cache_files = [
            '/path/to/cache/file.tmp',
            '/path/to/Cache/data.log',
            '/path/to/temp/session.dat'
        ]
        
        non_cache_files = [
            '/path/to/document.pdf',
            '/path/to/image.jpg',
            '/path/to/script.py'
        ]
        
        for cache_file in cache_files:
            assert self.optimizer._is_cache_file(cache_file)
        
        for non_cache_file in non_cache_files:
            assert not self.optimizer._is_cache_file(non_cache_file)
    
    def test_application_detection(self):
        """Test application detection from file paths"""
        test_cases = [
            ('/Users/test/Library/Caches/com.google.Chrome/data.db', 'Google Chrome'),
            ('/Users/test/.mozilla/firefox/cache/file.tmp', 'Mozilla Firefox'),
            ('/Users/test/Library/Unity/cache/project.log', 'Unity'),
            ('/random/path/file.txt', 'Unknown')
        ]
        
        for file_path, expected_app in test_cases:
            detected_app = self.optimizer._detect_application(file_path)
            assert detected_app == expected_app
    
    @patch('psutil.Process')
    def test_performance_metrics_recording(self, mock_process):
        """Test performance metrics recording"""
        # Mock memory info
        mock_memory = Mock()
        mock_memory.rss = 100 * 1024 * 1024  # 100MB
        mock_process.return_value.memory_info.return_value = mock_memory
        
        start_time = time.time()
        end_time = start_time + 1.0
        
        self.optimizer._record_performance_metrics(
            start_time, end_time, 1000, 10, 50000000, 4, 0
        )
        
        assert len(self.optimizer.performance_history) == 1
        
        metrics = self.optimizer.performance_history[0]
        assert metrics.total_files_scanned == 1000
        assert metrics.total_directories_scanned == 10
        assert metrics.threads_used == 4
    
    def test_performance_summary(self):
        """Test performance summary generation"""
        # Add some mock metrics
        with patch('psutil.Process') as mock_process:
            mock_memory = Mock()
            mock_memory.rss = 100 * 1024 * 1024
            mock_process.return_value.memory_info.return_value = mock_memory
            
            for i in range(5):
                start_time = time.time()
                self.optimizer._record_performance_metrics(
                    start_time, start_time + 1.0, 100, 1, 1000000, 2, 0
                )
        
        summary = self.optimizer.get_performance_summary()
        
        assert 'average_scan_time_seconds' in summary
        assert 'average_files_per_second' in summary
        assert 'total_scans_performed' in summary
        assert summary['total_scans_performed'] == 5

class TestOptimizedLazyScan:
    """Test suite for OptimizedLazyScan"""
    
    def setup_method(self):
        """Setup test environment"""
        self.lazy_scan = OptimizedLazyScan()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Cleanup test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('core.performance_optimizer.CacheAnalyzer')
    @patch('core.performance_optimizer.PluginManager')
    def test_optimized_scan_integration(self, mock_plugin_manager, mock_cache_analyzer):
        """Test integrated optimized scanning"""
        # Create test directory with files
        test_file = os.path.join(self.temp_dir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('test content')
        
        # Mock plugin manager
        mock_plugin_manager.return_value.get_cache_handlers.return_value = []
        
        # Mock cache analyzer
        mock_cache_analyzer.return_value.batch_analyze.return_value = []
        
        result = self.lazy_scan.scan_with_optimization([self.temp_dir])
        
        assert 'scan_summary' in result
        assert 'cache_analysis' in result
        assert 'plugin_enhancement' in result
        assert 'performance_metrics' in result
        
        scan_summary = result['scan_summary']
        assert scan_summary['total_files'] >= 1
        assert scan_summary['directories_scanned'] == 1
    
    def test_optimization_recommendations(self):
        """Test optimization recommendations"""
        recommendations = self.lazy_scan.get_optimization_recommendations()
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        assert all(isinstance(rec, str) for rec in recommendations)
```

---

## 📋 Implementation Checklist

### Phase 1: Foundation (Weeks 1-4)
- [ ] **Cross-Platform Abstraction Layer**
  - [ ] Implement `PlatformManager` base class
  - [ ] Create platform-specific implementations (macOS, Windows, Linux)
  - [ ] Add comprehensive platform detection
  - [ ] Implement platform-specific cache path discovery

- [ ] **Enhanced Security Integration**
  - [ ] Extend existing security framework
  - [ ] Add cross-platform security validations
  - [ ] Implement secure file operations for all platforms
  - [ ] Add comprehensive audit logging

### Phase 2: Intelligence (Weeks 5-8)
- [ ] **Intelligent Cache Analysis Engine**
  - [ ] Implement `CacheAnalyzer` with ML-ready architecture
  - [ ] Add risk assessment algorithms
  - [ ] Create usage pattern analysis
  - [ ] Implement safety scoring system

- [ ] **Plugin Architecture**
  - [ ] Design and implement `PluginManager`
  - [ ] Create plugin interface specifications
  - [ ] Develop core plugin types (cache handlers, analyzers, exporters)
  - [ ] Add plugin discovery and loading mechanisms

### Phase 3: Performance (Weeks 9-12)
- [ ] **Performance Optimization Suite**
  - [ ] Implement `ScanOptimizer` with multi-threading
  - [ ] Add intelligent thread allocation
  - [ ] Create performance monitoring and metrics
  - [ ] Implement scan result caching

- [ ] **Integration and Testing**
  - [ ] Integrate all components into `OptimizedLazyScan`
  - [ ] Comprehensive test suite development
  - [ ] Performance benchmarking
  - [ ] Cross-platform compatibility testing

### Quality Assurance
- [ ] **Code Quality**
  - [ ] Type hints for all public APIs
  - [ ] Comprehensive docstrings
  - [ ] Code coverage > 90%
  - [ ] Performance benchmarks

- [ ] **Security Review**
  - [ ] Security audit of all file operations
  - [ ] Penetration testing for plugin system
  - [ ] Validation of cross-platform security measures

---

## 🎯 Success Metrics

### Performance Targets
- **Scan Speed**: 10x improvement over current implementation
- **Memory Usage**: <500MB peak for large directory scans
- **Cross-Platform**: 100% feature parity across macOS, Windows, Linux
- **Plugin Ecosystem**: Support for 20+ application-specific plugins

### Quality Targets
- **Test Coverage**: >90% code coverage
- **Documentation**: Complete API documentation with examples
- **Security**: Zero critical security vulnerabilities
- **Reliability**: <0.1% error rate in production usage

This technical implementation guide provides the foundation for transforming LazyScan into a world-class, cross-platform disk management solution with enterprise-grade capabilities while maintaining its developer-focused approach and security-first design principles.