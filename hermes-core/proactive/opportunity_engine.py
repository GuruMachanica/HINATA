"""
HINATA Opportunity Engine (Disciplined Proactivity)
Evaluates whether background events warrant an interruption or silent logging.
Warashi-inspired interruptibility scoring. Strictly under 100 LOC.
"""

from typing import Dict, Any

class OpportunityEngine:
    def __init__(self, user_busy: bool = False, min_urgency_threshold: float = 0.7):
        self.user_busy = user_busy
        self.min_urgency = min_urgency_threshold

    def evaluate_telemetry(self, gpu_telemetry: Dict[str, Any], memory_telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """Examines system state and decides if HINATA should interrupt."""
        gpus = gpu_telemetry.get("gpus", [])
        if gpus:
            gpu = gpus[0]
            temp = gpu.get("temperature_c", 0)
            mem_pct = (gpu.get("memory_used_mb", 0) / max(gpu.get("memory_total_mb", 1), 1)) * 100
            
            # Critical VRAM or thermal event
            if temp > 85.0:
                return {
                    "should_interrupt": True,
                    "urgency": 0.95,
                    "reason": f"High GPU Temperature ({temp}°C)",
                    "message": f"Attention: Your RTX 4050 temperature is at {temp}°C."
                }
            if mem_pct > 95.0:
                return {
                    "should_interrupt": True,
                    "urgency": 0.85,
                    "reason": "VRAM Exhaustion Risk",
                    "message": f"VRAM is at {mem_pct:.1f}% capacity. Background tasks may fail."
                }

        # Normal operation: no interruption needed
        return {
            "should_interrupt": False,
            "urgency": 0.1,
            "reason": "System operating within nominal parameters",
            "message": None
        }
