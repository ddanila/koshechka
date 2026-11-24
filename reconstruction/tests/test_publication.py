"""Keep published links and the documented budget in sync with this checkout."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
from memory_budget import budget


class PublicationTests(unittest.TestCase):
    def test_local_documentation_links(self):
        for path in list(ROOT.glob('*.md')) + list((ROOT/'reconstruction').glob('*.md')) + [ROOT/'formal/README.md', ROOT/'native/README.md']:
            for link in re.findall(r'\]\(([^)]+)\)', path.read_text()):
                if ':' in link or link.startswith('#'):
                    continue
                self.assertTrue((path.parent/link.split('#')[0]).exists(), (path, link))

    def test_documented_memory_budget(self):
        data = budget()
        doc = (ROOT/'MEMORY-BUDGET.md').read_text()
        self.assertIn(f"**{data['native_total_bytes']}**", doc)
        self.assertIn(f"**{data['total_words45']}**", doc)
        self.assertIn(f"{data['nodes']} nodes, {data['leaves']} leaves, depth {data['max_tree_depth']}", doc)
        self.assertEqual(data['rows'][-1]['native_bytes']*8, 160*100)
