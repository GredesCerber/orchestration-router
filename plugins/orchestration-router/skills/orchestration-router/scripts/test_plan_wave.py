"""Synthetic offline decision tests; no real model IDs, processes or network."""
import unittest
from copy import deepcopy
from plan_wave import propose


def task(tid, **changes):
    value = {"id": tid, "mode": "read", "workspace": "main", "tier": 1, "risk": "low",
             "reads": [tid], "writes": [], "locks": [], "depends_on": [],
             "required_capabilities": ["read"], "data_class": "public", "acceptance": ["Evidence"]}
    value.update(changes)
    return value


def catalog():
    result = []
    for i, name in enumerate(["light", "standard", "deep"], 1):
        result.append({"id": name, "engine": "native", "model": "synthetic-" + name,
                       "tier": i, "enabled": True, "authorized": True, "status": "ready",
                       "evidence": "synthetic fixture", "cost_rank": i,
                       "capabilities": ["read", "write", "code"],
                       "efforts": ["low", "medium", "high"], "allowed_data_classes": ["public"]})
    return result


def manifest(tasks, **changes):
    value = {"tasks": tasks, "active": [], "done": [], "candidates": catalog(),
             "allowed_engines": ["native"], "max_workers": 3, "runtime_worker_slots": 3}
    value.update(changes)
    return value


class RoutingTests(unittest.TestCase):
    def test_depth_and_effort_are_selected(self):
        wave = propose(manifest([task("a"), task("b", tier=2), task("c", tier=3)]))["ready_wave"]
        self.assertEqual([(x["candidate"], x["requested_effort"]) for x in wave],
                         [("light", "low"), ("standard", "medium"), ("deep", "high")])
        self.assertTrue(all(x["actual_model"] is None and x["actual_effort"] is None for x in wave))

    def test_unknown_access_is_not_eligible(self):
        m = manifest([task("a")])
        for c in m["candidates"]:
            c["status"] = "unknown"
        self.assertFalse(propose(m)["ready_wave"])

    def test_data_and_engine_boundary(self):
        self.assertFalse(propose(manifest([task("a", data_class="personal")]))["ready_wave"])
        self.assertFalse(propose(manifest([task("a")], allowed_engines=["other"]))["ready_wave"])

    def test_explicit_model_not_substituted(self):
        self.assertFalse(propose(manifest([task("a", required_model="absent")]))["ready_wave"])

    def test_effort_control_and_explicit_unsupported(self):
        m = manifest([task("a", tier=3)])
        m["candidates"][2]["efforts"] = []
        self.assertIsNone(propose(m)["ready_wave"][0]["requested_effort"])
        m["tasks"][0]["effort"] = "ultra"
        self.assertFalse(propose(m)["ready_wave"])

    def test_readers_can_overlap_but_writer_waits(self):
        m = manifest([task("a", reads=["src"]), task("b", reads=["src/a.ts"]),
                      task("c", mode="write", reads=[], writes=["src/a.ts"])])
        self.assertEqual([x["task"] for x in propose(m)["ready_wave"]], ["a", "b"])

    def test_active_writer_blocks_case_insensitive_child_reader(self):
        m = manifest([task("a", reads=["SRC/ui/a.ts"])],
                     active=[{"id": "existing", "workspace": "main", "writes": ["src"]}])
        self.assertFalse(propose(m)["ready_wave"])

    def test_worktrees_isolate_files_but_not_named_resources(self):
        active = [{"id": "existing", "workspace": "wt-a", "writes": ["src"], "locks": ["build"]}]
        m = manifest([task("a", workspace="wt-b", reads=["src"]),
                      task("b", workspace="wt-b", locks=["build"])], active=active)
        self.assertEqual([x["task"] for x in propose(m)["ready_wave"]], ["a"])

    def test_session_cannot_run_twice(self):
        m = manifest([task("a", session="same")], active=[{"id": "other", "session": "same"}])
        self.assertFalse(propose(m)["ready_wave"])

    def test_dependencies_must_be_accepted(self):
        m = manifest([task("a"), task("b", depends_on=["a"])])
        self.assertEqual([x["task"] for x in propose(m)["ready_wave"]], ["a"])
        m["done"] = ["a"]
        self.assertEqual([x["task"] for x in propose(m)["ready_wave"]], ["b"])

    def test_cycles_and_unknown_dependencies_rejected(self):
        for tasks in [[task("a", depends_on=["b"]), task("b", depends_on=["a"])],
                      [task("a", depends_on=["absent"])]]:
            with self.assertRaises(ValueError):
                propose(manifest(tasks))

    def test_global_capacity_includes_active_descendants(self):
        m = manifest([task("a"), task("b"), task("c")],
                     active=[{"id": "claude-lead", "scope_free": True},
                             {"id": "claude-child", "scope_free": True}], max_workers=8)
        self.assertEqual(len(propose(m)["ready_wave"]), 1)

    def test_transient_error_does_not_spend_more_reasoning(self):
        self.assertFalse(propose(manifest([task("a", failure_kind="quota")]))["ready_wave"])
        wave = propose(manifest([task("a", failed_attempts=1)]))["ready_wave"]
        self.assertEqual(wave[0]["candidate"], "standard")
        self.assertFalse(propose(manifest([task("a", failed_attempts=2)]))["ready_wave"])

    def test_no_unscoped_writer_or_glob_or_traversal(self):
        for t in [task("a", mode="write"), task("a", reads=["src/*"]), task("a", reads=["../x"])]:
            with self.assertRaises(ValueError):
                propose(manifest([t]))

    def test_profile_does_not_make_light_task_maximal(self):
        m = manifest([task("a"), task("b", tier=2)], profile="quality")
        self.assertEqual([x["candidate"] for x in propose(m)["ready_wave"]], ["light", "deep"])

    def test_planning_does_not_mutate_manifest(self):
        m = manifest([task("a")])
        before = deepcopy(m)
        propose(m)
        self.assertEqual(m, before)

    def test_long_backlog_does_not_require_recursive_graph_walk(self):
        tasks = [task(str(i), depends_on=[str(i - 1)] if i else []) for i in range(2000)]
        result = propose(manifest(tasks))
        self.assertEqual([x["task"] for x in result["ready_wave"]], ["0"])
        self.assertEqual(len(result["waiting"]), 1999)

    def test_economy_soft_preference_does_not_override_cost(self):
        m = manifest([task("a", preferred_engine="claude")], profile="economy",
                     allowed_engines=["native", "claude"])
        expensive = deepcopy(m["candidates"][0])
        expensive.update(id="expensive", engine="claude", cost_rank=100)
        m["candidates"].append(expensive)
        self.assertEqual(propose(m)["ready_wave"][0]["candidate"], "light")

    def test_missing_read_scope_is_not_treated_as_no_access(self):
        with self.assertRaises(ValueError):
            propose(manifest([task("a", reads=[])]))
        result = propose(manifest([task("a", reads=[], scope_free=True)],
                                  active=[{"id": "writer", "writes": ["."]}]))
        self.assertEqual(len(result["ready_wave"]), 1)

    def test_unknown_active_scope_reserves_whole_workspace(self):
        self.assertFalse(propose(manifest([task("a")], active=[{"id": "unknown"}]))["ready_wave"])

    def test_exhausted_route_blocks_its_whole_pool(self):
        m = manifest([task("a")])
        for c in m["candidates"]:
            c["pool"] = "shared"
        m["candidates"][2]["status"] = "quota_exhausted"
        result = propose(m)
        self.assertFalse(result["ready_wave"])
        self.assertEqual(result["exhausted_pools"], ["shared"])

    def test_exhausted_pool_listed_by_coordinator(self):
        m = manifest([task("a")], exhausted_pools=["light-pool"])
        m["candidates"][0]["pool"] = "light-pool"
        self.assertEqual(propose(m)["ready_wave"][0]["candidate"], "standard")

    def test_status_typo_is_rejected(self):
        m = manifest([task("a")])
        m["candidates"][0]["status"] = "quota-exhausted"
        with self.assertRaises(ValueError):
            propose(m)


if __name__ == "__main__":
    unittest.main()
