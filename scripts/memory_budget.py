"""Estimate a compact native data layout, not Python RSS or executable size."""
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'reconstruction'))
from kitty.core import initial_legs
from kitty.geometry import cat


def budget():
    legs = initial_legs()
    tree, _ = cat({'t': 0., 'legs': [leg.state for leg in legs]})
    nodes = []

    def visit(node, depth):
        nodes.append((node, depth))
        for child in node.children:
            visit(child, depth + 1)

    visit(tree, 1)
    depth = max(d for _, d in nodes)
    rows = []

    def row(name, native_bytes, words, assumption):
        rows.append(dict(component=name, native_bytes=native_bytes,
                         words45=words, assumption=assumption))

    # Native: float64 scalars, uint32 flags/indices, no heap/object headers.
    # Historical comparison: one word per working scalar, not bit-equivalent floats.
    row('Four-leg state', 4*(15*8 + 4*4), 4*(15+4),
        'Per leg: state[4], K[8] including unused K0, previous dx, length, landing end; four integer tags/counters. No names/history.')
    row('Shared constants and body state', 16*8, 16,
        'Allowance of 16 scalar slots for constants, clock, speed, displacement and loop control.')
    row('RK4 workspace', 28*8, 28,
        'One leg at a time: state[4], four derivative vectors[16], trial[4], result[4].')
    row('Phase fitting workspace', 19*8, 19,
        'Four phases, offsets, targets, errors, plus three accumulators.')
    row('Leg-shape workspace', 24*8, 24,
        '24 scalar slots; includes complex arithmetic represented as scalar pairs. Library internals excluded.')
    child_words = sum(math.ceil((len(n.children)+1)/3) for n, _ in nodes if n.children)
    row('Geometry and topology', len(nodes)*(11*8+2*4), len(nodes)*5+child_words,
        'Native: 11 dimensions/pose scalars and first-child/next-sibling indices per node. Paper pp.199–200: four parameter words, one header, child lists packed three fields per word (one count field).')
    row('Traversal stack', depth*(13*8+4), depth*14,
        'Per level: origin[3], rotation[9], scale, child cursor; cursor uses uint32 in native layout.')
    row('Projection and hull workspace', 64*8, 64,
        'One primitive: 24 vertex scalars, 16 projected coordinates and 24 hull/scratch scalars.')
    row('Packed occupancy bitmap', 160*100//8, math.ceil(160*100/45),
        '160 by 100 cells, one bit per cell. This grid is our display choice, not recovered printer resolution.')
    return {
        'nodes': len(nodes), 'leaves': sum(not n.children for n, _ in nodes),
        'max_tree_depth': depth, 'rows': rows,
        'native_total_bytes': sum(r['native_bytes'] for r in rows),
        'total_words45': sum(r['words45'] for r in rows),
        'modern_display_buffers_excluded': {'occupancy_L_bytes': 160*100,
                                            'RGB_frame_bytes': 960*600*3},
        'excluded': ['executable instructions', 'math-library code/internal workspace',
                     'OS and I/O buffers', 'Python/Pillow objects and allocator',
                     'film/JSON/frame histories', 'diagnostic UI'],
    }


if __name__ == '__main__':
    print(json.dumps(budget(), indent=2))
