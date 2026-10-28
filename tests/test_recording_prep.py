"""Recording material consistency checks; no API or model recomputation."""
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from bluebikes.analysis import _demo
from bluebikes.human_review import load_reviews
from bluebikes.presentation import executive_summary

ROOT = Path(__file__).resolve().parents[1]


class RecordingPreparationTests(unittest.TestCase):
    def narration(self):
        text = (ROOT / "docs/DEMO_SCRIPT.md").read_text(encoding="utf-8")
        return re.findall(r"<!-- NARRATION_START -->\n(.*?)\n<!-- NARRATION_END -->", text, re.S)

    def test_saved_numeric_example_matches_markdown_app_and_script(self):
        chain = pd.read_csv(ROOT / "results/focused_event_chain.csv")
        example = chain[chain.event_increment_handling_actions.gt(0)].iloc[0]
        html = executive_summary(chain)
        readme = (ROOT / "README.md").read_text(encoding="utf-8").replace("**", "")
        for value in [
            f"{int(example.full_time_base)} → {int(example.full_time_scenario)}",
            f"{chr(36)}{example.crew_cost_base:,.0f} → {chr(36)}{example.crew_cost_scenario:,.0f}",
            f"+{example.event_increment_handling_actions:,.0f}",
            "March 2026", "Boston / April 2026",
            "Bluebikes is Greater Boston’s bike-share system.",
            "not actual Bluebikes crew deployment",
        ]:
            self.assertIn(value, html)
            self.assertIn(value, readme)
        speech = " ".join(self.narration())
        self.assertIn(f"{int(example.full_time_base)} to {int(example.full_time_scenario)}", speech)
        self.assertIn(f"{chr(36)}{example.crew_cost_base:,.0f} to {chr(36)}{example.crew_cost_scenario:,.0f}", speech)

    def test_runsheet_matches_narration_and_count(self):
        paragraphs = self.narration()
        self.assertEqual(len(paragraphs), 6)
        sheet = (ROOT / "docs/RECORDING_RUNSHEET.md").read_text(encoding="utf-8")
        for paragraph in paragraphs:
            self.assertIn("| " + paragraph + " |", sheet)
        speech = " ".join(paragraphs)
        self.assertEqual(len(speech.split()), 307)
        expansions = {
            "2024–2025": "twenty twenty-four and twenty twenty-five",
            "January–September": "January through September",
            "2026": "twenty twenty-six", "3,000": "three thousand",
            "$72,000": "seventy-two thousand dollars",
            "$78,000": "seventy-eight thousand dollars", "120": "one hundred twenty",
        }
        for short, long in expansions.items():
            speech = speech.replace(short, long)
        self.assertEqual(len(speech.split()), 322)
        self.assertIn("Human spoken end-to-end rehearsal:** NOT MEASURED", sheet)

    def test_existing_generator_preserves_current_script_without_calculation(self):
        reviews = load_reviews(ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            (target / "docs").mkdir()
            with patch("bluebikes.human_review.load_reviews", return_value=reviews), \
                 patch("bluebikes.app_service.extract_event", side_effect=AssertionError("No API")):
                _demo(json.loads((ROOT / "results/summary.json").read_text(encoding="utf-8")), target)
            self.assertEqual((target / "docs/DEMO_SCRIPT.md").read_text(encoding="utf-8"),
                             (ROOT / "docs/DEMO_SCRIPT.md").read_text(encoding="utf-8"))

    def test_readme_order_and_overlay_scope(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        titles = ["### The problem", "### The decision", "### AI + analytics",
                  "### Illustrative scenario", "## How it works",
                  "docs/diagrams/bluebikes_flow.svg", "## Submission materials"]
        positions = [readme.index(title) for title in titles]
        self.assertEqual(positions, sorted(positions))
        srt = (ROOT / "docs/recording_overlays.srt").read_text(encoding="utf-8")
        self.assertEqual(srt, (ROOT / "deliverables/demo/bluebikes_demo_en.srt").read_text(encoding="utf-8"))
        self.assertEqual(len(srt.strip().split("\n\n")), 35)
        self.assertIn("Nine other cities share one pool", srt)
        sheet = (ROOT / "docs/RECORDING_RUNSHEET.md").read_text(encoding="utf-8")
        self.assertIn("Rendered output:** 175.00 seconds", sheet)
        self.assertIn("No API click", sheet)
