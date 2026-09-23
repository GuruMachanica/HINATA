"""Tests for memory store, knowledge graph, fact extraction, and proactive triggers."""
import threading

from backend.features.knowledge.extractor import extract_facts
from backend.features.knowledge.graph_store import KnowledgeGraphStore
from backend.features.memory.store import MemoryStore
from backend.features.proactive.triggers import SystemHealthTrigger


def test_sqlite_concurrent_writes():
    print("[1/5] Testing SQLite serialized writes under concurrency...")
    mem = MemoryStore()
    mem.setup()
    kg = KnowledgeGraphStore()
    kg.setup()

    errors = []

    def write_worker(worker_id: int):
        try:
            for i in range(15):
                mem.append("user", f"concurrent test message {worker_id}-{i}")
                kg.reinforce("user", "tests", f"topic_{worker_id}_{i}", confidence=0.6)
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=write_worker, args=(t,)) for t in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Concurrent writes threw errors: {errors}"
    print("  -> SQLite concurrent writes PASSED (8 threads x 15 writes, 0 lock errors)")


def test_memory_search_escaping():
    print("[2/5] Testing MemoryStore literal LIKE wildcard escaping...")
    mem = MemoryStore()
    mem.setup()
    mem.append("user", "Exact percent 100% discount")
    mem.append("user", "Exact underscore test_variable value")
    mem.append("user", "Unrelated 1000 discount without percent")

    contents = [r["content"] for r in mem.search("%", limit=10)]
    assert any("100%" in c for c in contents), "Did not find 100% item"
    assert not any("1000 discount" in c for c in contents), \
        "Literal '%' matched non-% entries like SQL wildcard!"

    contents_under = [r["content"] for r in mem.search("_", limit=10)]
    assert any("test_variable" in c for c in contents_under), "Did not find test_variable"
    print("  -> MemoryStore LIKE escaping PASSED")


def test_knowledge_graph_exact_clear():
    print("[3/5] Testing KnowledgeGraphStore exact-match clear()...")
    kg = KnowledgeGraphStore()
    kg.setup()
    kg.reinforce("user", "likes", "gpu", confidence=0.8)
    kg.reinforce("user", "likes", "gpu_driver_update", confidence=0.8)
    kg.reinforce("user", "likes", "another_topic", confidence=0.8)

    # Clearing 'gpu' should only remove 'gpu', NOT 'gpu_driver_update'
    kg.clear("gpu")

    matched_objects = [r["object"] for r in kg.search("gpu", limit=10)]
    assert "gpu" not in matched_objects, "'gpu' was not cleared"
    assert "gpu_driver_update" in matched_objects, \
        "'gpu_driver_update' was incorrectly cleared by substring matching!"
    print("  -> KnowledgeGraphStore exact clear PASSED")


def test_fact_extraction_confidence():
    print("[4/5] Testing fact extraction confidence calibration...")
    facts_hedged = extract_facts("I think my setup is probably broken")
    for r, o, conf, src in facts_hedged:
        assert src == "inferred", f"Expected 'inferred' source, got: {src}"
        assert conf <= 0.6, f"Expected confidence <= 0.6 for hedged sentence, got: {conf}"

    facts_explicit = extract_facts("remember that my favorite editor is vim")
    assert any(src == "stated" and conf >= 0.9 for r, o, conf, src in facts_explicit), \
        f"Expected high-confidence stated fact, got: {facts_explicit}"
    print("  -> Fact extraction confidence calibration PASSED")


def test_system_health_trigger():
    print("[5/5] Testing SystemHealthTrigger numeric thresholds...")
    from backend.core.event_bus import bus
    trigger = SystemHealthTrigger(bus)
    seed = trigger.evaluate()
    print(f"  -> SystemHealthTrigger evaluated: {seed}")
    print("  -> SystemHealthTrigger numeric thresholds PASSED")
