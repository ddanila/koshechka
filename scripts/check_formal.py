"""Reject unfinished proofs and record the actual axiom audit from Lean."""
from pathlib import Path
import re
import shutil
import subprocess

root=Path(__file__).resolve().parents[1]/'formal'
source=(root/'Koshechka.lean').read_text()
assert not re.search(r'\b(sorry|admit)\b|^\s*(axiom|constant)\s',source,re.MULTILINE)
lake=shutil.which('lake') or str(Path.home()/'.elan/bin/lake')
subprocess.run([lake,'build'],cwd=root,check=True)
result=subprocess.run([lake,'env','lean','Koshechka.lean'],cwd=root,check=True,text=True,capture_output=True)
assert 'sorryAx' not in result.stdout
for dependencies in re.findall(r'depends on axioms: \[([^]]*)\]',result.stdout):
    assert set(dependencies.split(', ')) <= {'propext','Classical.choice','Quot.sound'},dependencies
assert len(re.findall('depends on axioms:',result.stdout))>=8
print(result.stdout)
