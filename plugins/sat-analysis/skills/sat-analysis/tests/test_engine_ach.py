"""ACH engine boundary tests: provenance, qualified results, and recomputation."""

from __future__ import annotations

import copy
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sat_engine.ach import compute_matrix
from sat_engine.validators import ValidationFailure, validate


def observation(record_id: str, **metadata: object) -> dict[str, object]:
    return {
        "schema_version": "1", "id": record_id, "raw": f"Raw observation {record_id}",
        "source": f"source/{record_id}", "parse_status": "parsed", **metadata,
    }


def evidence(record_id: str, observation_id: str,
             ratings: dict[str, str] | None = None, **metadata: object) -> dict[str, object]:
    return {
        "schema_version": "1", "id": record_id, "observation_id": observation_id,
        "ratings": {"H1": "+", "H2": "N"} if ratings is None else ratings, **metadata,
    }


def request(**fields: object) -> dict[str, object]:
    return {
        "schema_version": "1", "mode": "FULL", "submode": "GENERAL",
        "question": "What explains the observations?",
        "hypotheses": [
            {"schema_version": "1", "id": "H1", "description": "Transport degradation"},
            {"schema_version": "1", "id": "H2", "description": "Telemetry artifact"},
        ],
        "observations": [observation("O1")],
        "evidence": [evidence("E1", "O1")], **fields,
    }


class EngineMatrixTests(unittest.TestCase):
    def test_schema_shape_and_input_immutability(self) -> None:
        data = request()
        for kind in ("observations", "hypotheses", "evidence"):
            for record in data[kind]:
                record.pop("schema_version")
        original = copy.deepcopy(data)
        result = compute_matrix(data)
        self.assertEqual(data, original)
        self.assertEqual(set(result), {
            "schema_version", "title", "relationship", "hypotheses", "evidence",
            "assessment", "sensitivity", "diagnosticity",
        })
        validate("ach_matrix", result)
        self.assertEqual(result["schema_version"], "1")
        self.assertTrue(all(h["schema_version"] == "1" for h in result["hypotheses"]))
        self.assertTrue(all(e["schema_version"] == "1" for e in result["evidence"]))
        self.assertNotIn("initial_probability", result["hypotheses"][0])
        result["evidence"][0]["ratings"]["H1"] = "--"
        self.assertEqual(data, original)

    def test_inherited_provenance_controls_sensitivity_and_reliability(self) -> None:
        data = request(
            observations=[observation("O1", source="collector", source_id="C1", reliability="F",
                                      origin_id="measurement", dependency_groups=["upstream"])],
            evidence=[evidence("E1", "O1", {"H1": "+", "H2": "--"}, rationale="Analyst explanation")],
        )
        result = compute_matrix(data)
        self.assertEqual(result["evidence"], data["evidence"])
        for key in ("source:collector", "source_id:C1", "origin:measurement", "dependency:upstream"):
            self.assertEqual(result["sensitivity"]["group_impact"][key]["removed_evidence_ids"], ["E1"])
        contradiction = result["assessment"]["contradictions"]["H2"][0]
        self.assertEqual(contradiction["description"], "Raw observation O1")
        self.assertEqual(contradiction["origin_id"], "measurement")
        self.assertTrue(any("unknown or unjudged" in c for c in result["assessment"]["caveats"]))
        scores = result["assessment"]["scores"]
        data["observations"][0]["reliability"] = "A"
        self.assertEqual(compute_matrix(data)["assessment"]["scores"], scores)

    def test_evidence_cannot_override_observation_provenance_even_if_equal(self) -> None:
        for field, value in {
            "source": "different", "source_id": "different", "reliability": "A",
            "origin_id": "different", "dependency_groups": ["different"],
            "description": "An interpretation cannot replace raw observation text",
        }.items():
            with self.subTest(field=field), self.assertRaises(ValidationFailure):
                compute_matrix(request(evidence=[evidence("E1", "O1", **{field: value})]))
        with self.assertRaises(ValidationFailure):
            compute_matrix(request(evidence=[evidence("E1", "O1", source="source/O1")]))

    def test_repeated_observation_references_contribute_once_without_synthetic_origin(self) -> None:
        base = compute_matrix(request())
        duplicate = compute_matrix(request(evidence=[evidence("E1", "O1"), evidence("E2", "O1")]))
        self.assertEqual(duplicate["assessment"]["scores"], base["assessment"]["scores"])
        self.assertEqual(duplicate["assessment"]["contributing_record_count"], 1)
        self.assertFalse(duplicate["sensitivity"]["evidence_impact"]["E1"]["changes_assessment"])
        self.assertEqual(duplicate["sensitivity"]["group_impact"]["source:source/O1"]["removed_evidence_ids"],
                         ["E1", "E2"])
        self.assertTrue(all(not key.startswith("origin:")
                            for key in duplicate["sensitivity"]["group_impact"]))

    def test_origin_and_observation_namespaces_do_not_collide(self) -> None:
        result = compute_matrix(request(
            observations=[observation("same"), observation("different", origin_id="same")],
            evidence=[evidence("E1", "same"), evidence("E2", "different")],
        ))
        self.assertEqual(result["assessment"]["contributing_record_count"], 2)
        self.assertEqual(result["assessment"]["scores"]["H1"], 2)

    def test_same_observation_or_origin_conflicting_ratings_fail(self) -> None:
        for use_origin in (False, True):
            observations = [observation("O1", origin_id="original")]
            second_ref = "O1"
            if use_origin:
                observations.append(observation("O2", origin_id="original"))
                second_ref = "O2"
            for conflicting in ({"H1": "-", "H2": "N"}, {"H1": "+"}):
                with self.subTest(origin=use_origin, ratings=conflicting):
                    with self.assertRaisesRegex(ValidationFailure, "Conflicting ratings"):
                        compute_matrix(request(observations=observations, evidence=[
                            evidence("E1", "O1"), evidence("E2", second_ref, conflicting),
                        ]))

    def test_derivative_origin_dedup_and_dependency_removal_use_all_publications(self) -> None:
        data = request(
            observations=[
                observation("O1", source="collector", origin_id="measurement", dependency_groups=["shared"]),
                observation("O2", source="bulletin", origin_id="measurement"),
                observation("O3", source="independent"),
            ],
            evidence=[evidence("E1", "O1"), evidence("E2", "O2"),
                      evidence("E3", "O3", {"H1": "N", "H2": "N"})],
        )
        result = compute_matrix(data)
        self.assertEqual(result["assessment"]["scores"]["H1"], 1)
        self.assertEqual(result["assessment"]["contributing_record_count"], 2)
        for key in ("dependency:shared", "source:collector", "origin:measurement"):
            impact = result["sensitivity"]["group_impact"][key]
            self.assertEqual(impact["removed_evidence_ids"], ["E1", "E2"])
            self.assertEqual(impact["status"], "underdetermined")
            self.assertTrue(impact["changes_assessment"])

    def test_distinct_measurements_same_source_are_not_deduplicated(self) -> None:
        for metadata, key in (({"source": "collector"}, "source:collector"),
                              ({"source_id": "collector-id"}, "source_id:collector-id")):
            with self.subTest(metadata=metadata):
                result = compute_matrix(request(
                    observations=[observation("sent", **metadata), observation("received", **metadata),
                                  observation("independent")],
                    evidence=[evidence("E1", "sent"), evidence("E2", "received"),
                              evidence("E3", "independent", {"H1": "N", "H2": "N"})],
                ))
                self.assertEqual(result["assessment"]["scores"]["H1"], 2)
                self.assertEqual(result["assessment"]["contributing_record_count"], 3)
                self.assertTrue(all(not impact["changes_assessment"]
                                    for impact in result["sensitivity"]["evidence_impact"].values()))
                self.assertTrue(result["sensitivity"]["group_impact"][key]["changes_assessment"])
                self.assertFalse(result["sensitivity"]["heuristic_stable"])

    def test_incomplete_differs_from_neutral_and_has_no_variance(self) -> None:
        result = compute_matrix(request(evidence=[evidence("E1", "O1", {"H1": "N"})]))
        self.assertEqual(result["assessment"]["status"], "incomplete")
        self.assertEqual(result["assessment"]["missing_ratings"], [{"evidence_id": "E1", "hypothesis_id": "H2"}])
        self.assertIsNone(result["diagnosticity"]["E1"])
        self.assertIsNone(result["assessment"]["winner"])
        self.assertIsNone(result["sensitivity"]["heuristic_stable"])
        neutral = compute_matrix(request(evidence=[evidence("E1", "O1", {"H1": "N", "H2": "N"})]))
        self.assertEqual(neutral["assessment"]["status"], "underdetermined")
        self.assertEqual(neutral["diagnosticity"]["E1"], 0)

    def test_empty_and_incomplete_full_inputs_remain_valid(self) -> None:
        for fields in ({"evidence": []}, {"hypotheses": [], "evidence": []},
                       {"hypotheses": [], "evidence": [evidence("E1", "O1", {})]}):
            with self.subTest(fields=fields):
                result = compute_matrix(request(**fields))
                self.assertEqual(result["assessment"]["status"], "insufficient_evidence")
                self.assertEqual(result["assessment"]["heuristic_leaders"], [])
                self.assertIsNone(result["assessment"]["winner"])

    def test_combined_causes_and_analyst_judgment_do_not_become_computed_winner(self) -> None:
        data = request(relationship="overlapping")
        data["hypotheses"].append({"schema_version": "1", "id": "H3", "description": "Both causes"})
        for hypothesis in data["hypotheses"]:
            hypothesis["initial_probability"] = 0.8
        data["evidence"][0]["ratings"] = {"H1": "+", "H2": "+", "H3": "++"}
        data["judgment"] = {"summary": "Transport effects merit a bounded response.",
                            "selected_hypothesis_ids": ["H1"]}
        result = compute_matrix(data)
        self.assertEqual(result["assessment"]["heuristic_leaders"], ["H3"])
        self.assertEqual(result["assessment"]["status"], "differentiated")
        self.assertIsNone(result["assessment"]["winner"])
        self.assertNotIn("confidence", result["assessment"])
        self.assertNotIn("likelihood", result["assessment"])
        self.assertEqual(data["judgment"]["selected_hypothesis_ids"], ["H1"])

    def test_duplicate_ids_dangling_references_and_unknown_ratings_fail(self) -> None:
        variants = []
        for kind in ("hypotheses", "observations", "evidence"):
            data = request()
            data[kind].append(copy.deepcopy(data[kind][0]))
            variants.append(data)
        variants.append(request(evidence=[evidence("E1", "missing")]))
        variants.append(request(evidence=[evidence("E1", "O1", {"missing": "+"})]))
        variants.append(request(evidence=[evidence("E1", "O1", {"H1": "maybe"})]))
        for data in variants:
            with self.subTest(data=data), self.assertRaises(ValidationFailure):
                compute_matrix(data)

    def test_probability_relationships_preserve_missing_values(self) -> None:
        cases = [
            ("exclusive_exhaustive", [0.2, None], True),
            ("exclusive_exhaustive", [0.2, 0.8], True),
            ("exclusive_exhaustive", [0.2, 0.3], False),
            ("exclusive_nonexhaustive", [0.2, 0.3], True),
            ("exclusive_nonexhaustive", [0.8, 0.8], False),
            ("overlapping", [0.8, 0.8], True),
            ("unspecified", [0.8, 0.8], True),
        ]
        for relationship, probabilities, valid in cases:
            data = request(relationship=relationship)
            for hypothesis, probability in zip(data["hypotheses"], probabilities):
                hypothesis["initial_probability"] = probability
            with self.subTest(relationship=relationship, probabilities=probabilities):
                if valid:
                    result = compute_matrix(data)
                    self.assertEqual([h["initial_probability"] for h in result["hypotheses"]], probabilities)
                else:
                    with self.assertRaises(ValidationFailure):
                        compute_matrix(data)

    def test_known_exclusive_mass_above_one_is_invalid_even_with_missing_values(self) -> None:
        for relationship in ("exclusive_exhaustive", "exclusive_nonexhaustive"):
            data = request(relationship=relationship)
            for hypothesis in data["hypotheses"]:
                hypothesis["initial_probability"] = 0.8
            data["hypotheses"].append({"id": "H3", "description": "Unquantified alternative"})
            with self.subTest(relationship=relationship), self.assertRaises(ValidationFailure):
                compute_matrix(data)

    def test_nonfinite_boolean_and_nonpoint_probabilities_fail(self) -> None:
        for value in (math.nan, math.inf, -math.inf, True, False, -0.1, 1.1, [0.2, 0.4], "0.3", 10 ** 1000):
            data = request()
            data["hypotheses"][0]["initial_probability"] = value
            with self.subTest(value=str(value)[:40]), self.assertRaises(ValidationFailure):
                compute_matrix(data)

    def test_missing_and_f_reliability_are_unknown_without_confidence_caps(self) -> None:
        results = []
        for metadata in ({}, {"reliability": "F"}, {"reliability": "unknown"}, {"reliability": "A"}):
            results.append(compute_matrix(request(observations=[observation("O1", **metadata)])))
        for result in results:
            self.assertEqual(result["assessment"]["scores"], {"H1": 1, "H2": 0})
            self.assertIsNone(result["assessment"]["winner"])
        for result in results[:3]:
            self.assertTrue(any("unknown or unjudged" in c for c in result["assessment"]["caveats"]))

    def test_reordering_does_not_change_assessment_or_sensitivity(self) -> None:
        data = request(observations=[observation("O1"), observation("O2")],
                       evidence=[evidence("E1", "O1"), evidence("E2", "O2", {"H1": "N", "H2": "+"})])
        original = compute_matrix(data)
        for kind in ("hypotheses", "observations", "evidence"):
            data[kind].reverse()
        reordered = compute_matrix(data)
        for field in ("assessment", "sensitivity", "diagnosticity"):
            self.assertEqual(original[field], reordered[field])

    def test_rating_object_key_order_does_not_change_canonical_computation(self) -> None:
        ratings = {f"H{i}": value for i, value in enumerate(["++", "N", "+", "--", "-", "N", "+"])}
        data = request(
            hypotheses=[{"id": key, "description": key} for key in ratings],
            evidence=[evidence("E1", "O1", ratings)],
        )
        original = compute_matrix(data)
        data["evidence"][0]["ratings"] = dict(reversed(list(ratings.items())))
        self.assertEqual(compute_matrix(data), original)

    def test_forged_computation_is_not_an_input_and_returned_objects_are_not_cached(self) -> None:
        data = request()
        original = compute_matrix(data)
        forged = compute_matrix(data)
        forged["assessment"]["winner"] = "H1"
        forged["assessment"]["scores"]["H1"] = 9999
        forged["sensitivity"]["heuristic_stable"] = True
        self.assertEqual(compute_matrix(data), original)
        for field in ("assessment", "sensitivity", "diagnosticity", "scores"):
            with self.subTest(field=field), self.assertRaises(ValidationFailure):
                compute_matrix({**data, field: forged.get(field, {})})

    def test_light_mode_cannot_smuggle_ratings(self) -> None:
        with self.assertRaises(ValidationFailure):
            compute_matrix(request(mode="LIGHT"))


if __name__ == "__main__":
    unittest.main()
