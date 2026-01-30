"""
Memory - Long-term memory management
Stores user preferences, environment, and repeated decisions
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime


class Memory:
    """
    Long-term memory for the agent
    
    Stores:
    - User preferences (language, output granularity, forbidden operations)
    - Environment (OS, work directory, network availability)
    - Repeated decisions (common commands, naming conventions)
    """
    
    def __init__(self, memory_file: Optional[str] = None):
        self.memory_file = Path(memory_file) if memory_file else Path('./data/memory.json')
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.data = {
            'version': '1.0',
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'user_preferences': {},
            'environment': {},
            'repeated_decisions': {},
            'facts': {},
        }
        
        self.load()
    
    def load(self) -> None:
        """Load memory from file"""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    self.data.update(loaded)
            except Exception as e:
                print(f"Warning: Failed to load memory: {e}")
    
    def save(self) -> None:
        """Save memory to file"""
        self.data['last_updated'] = datetime.now().isoformat()
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Failed to save memory: {e}")
    
    def set_preference(self, key: str, value: Any) -> None:
        """
        Set a user preference
        
        Examples:
        - set_preference('language', 'en')
        - set_preference('output_granularity', 'detailed')
        - set_preference('forbidden_operations', ['rm -rf', 'sudo'])
        """
        self.data['user_preferences'][key] = value
        self.save()
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference"""
        return self.data['user_preferences'].get(key, default)
    
    def set_environment(self, key: str, value: Any) -> None:
        """
        Set environment information
        
        Examples:
        - set_environment('os', 'Linux')
        - set_environment('work_dir', '/home/user/projects')
        - set_environment('network_available', True)
        """
        self.data['environment'][key] = value
        self.save()
    
    def get_environment(self, key: str, default: Any = None) -> Any:
        """Get environment information"""
        return self.data['environment'].get(key, default)
    
    def record_decision(self, category: str, key: str, value: Any) -> None:
        """
        Record a repeated decision
        
        Examples:
        - record_decision('commands', 'list_files', 'ls -la')
        - record_decision('naming', 'test_files_prefix', 'test_')
        """
        if category not in self.data['repeated_decisions']:
            self.data['repeated_decisions'][category] = {}
        
        self.data['repeated_decisions'][category][key] = {
            'value': value,
            'recorded_at': datetime.now().isoformat()
        }
        self.save()
    
    def get_decision(self, category: str, key: str, default: Any = None) -> Any:
        """Get a recorded decision"""
        if category not in self.data['repeated_decisions']:
            return default
        
        decision = self.data['repeated_decisions'][category].get(key)
        if decision is None:
            return default
        
        return decision.get('value', default)
    
    def record_fact(self, category: str, fact: str) -> None:
        """
        Record a fact discovered during execution
        
        Examples:
        - record_fact('file_structure', '/home/user/projects contains: src/, tests/, docs/')
        - record_fact('system_info', 'Python 3.10.12 installed')
        """
        if category not in self.data['facts']:
            self.data['facts'][category] = []
        
        self.data['facts'][category].append({
            'fact': fact,
            'recorded_at': datetime.now().isoformat()
        })
        self.save()
    
    def get_facts(self, category: Optional[str] = None) -> Dict[str, List[str]]:
        """Get recorded facts, optionally filtered by category"""
        if category:
            return {
                category: [
                    f['fact'] for f in self.data['facts'].get(category, [])
                ]
            }
        
        return {
            cat: [f['fact'] for f in facts]
            for cat, facts in self.data['facts'].items()
        }
    
    def to_context(self, max_chars: int = 2000) -> str:
        """
        Convert memory to a compact context string for LLM prompts
        Truncate if too large
        """
        parts = []
        
        # User preferences
        if self.data['user_preferences']:
            parts.append("## User Preferences")
            for key, value in self.data['user_preferences'].items():
                parts.append(f"- {key}: {value}")
        
        # Environment
        if self.data['environment']:
            parts.append("\n## Environment")
            for key, value in self.data['environment'].items():
                parts.append(f"- {key}: {value}")
        
        # Recent facts
        if self.data['facts']:
            parts.append("\n## Known Facts")
            for category, facts in self.data['facts'].items():
                recent = facts[-3:] if len(facts) > 3 else facts  # Last 3 per category
                for fact in recent:
                    parts.append(f"- {category}: {fact['fact']}")
        
        context = '\n'.join(parts)
        
        # Truncate if needed
        if len(context) > max_chars:
            context = context[:max_chars] + "\n... (truncated)"
        
        return context or "(No memory yet)"
    
    def clear(self) -> None:
        """Clear all memory (use with caution!)"""
        if self.memory_file.exists():
            self.memory_file.unlink()
        
        self.data = {
            'version': '1.0',
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'user_preferences': {},
            'environment': {},
            'repeated_decisions': {},
            'facts': {},
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Return memory as dictionary"""
        return self.data.copy()
    
    def summary(self) -> str:
        """Get a summary of memory contents"""
        return f"""
Memory Summary:
- Preferences: {len(self.data['user_preferences'])} items
- Environment: {len(self.data['environment'])} items
- Decisions: {sum(len(v) for v in self.data['repeated_decisions'].values())} recorded
- Facts: {sum(len(v) for v in self.data['facts'].values())} discoveries
- Last updated: {self.data['last_updated']}
        """
