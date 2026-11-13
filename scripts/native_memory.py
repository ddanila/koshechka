"""Record native storage, compiler stack reports and object sections."""
import argparse
import json
from pathlib import Path
import platform
import subprocess

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--binary',type=Path,default=Path('native/build/kitty'))
parser.add_argument('--cc',default='cc')
args=parser.parse_args()
binary=args.binary.resolve()
rows=[]
for source in ('main','core','geometry'):
    for line in (binary.parent/(source+'.su')).read_text().splitlines():
        location,count,kind=line.split('\t')
        rows.append(dict(function=location.rsplit(':',1)[-1],bytes=int(count),kind=kind))
assert all(r['kind'] in ('static','dynamic,bounded') for r in rows),rows
# All application frames summed once is conservative for nonrecursive calls;
# visit is the sole recursive function, with maximum tree depth four.
stack_bound=sum(r['bytes']*(4 if r['function']=='visit' else 1) for r in rows)
report=dict(platform=platform.platform(),
            compiler=subprocess.check_output([args.cc,'--version'],text=True).splitlines()[0],
            storage=json.loads(subprocess.check_output([str(binary),'--memory'])),
            preset_constant_bytes=2*json.loads(subprocess.check_output([str(binary),'--memory']))['nodes_bytes'],stack_frames=rows,
            conservative_application_stack_bound_bytes=stack_bound,
            object_sections=subprocess.check_output(['size',*[str(binary.parent/(s+'.o')) for s in ('main','core','geometry')]],text=True).replace(str(binary.parent)+'/', ''),
            executable_file_bytes=binary.stat().st_size,
            exclusions=['libc/libm internal stack and storage','loader and shared libraries','stdio buffering','OS process overhead'],
            note='Legs/nodes reside in main stack: do not add their sizes to the stack bound. Preset constants occupy read-only object sections. This is not BESM executable size.')
print(json.dumps(report,indent=2))
