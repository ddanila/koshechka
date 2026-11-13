"""Build GitHub Pages from an explicit public-asset allowlist."""
import argparse
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ['index.html', 'viewer.js', 'analysis.js'] + [
    'output/' + name for name in (
        'animation.js', 'kitty.gif', 'kitty.mp4', 'kitty-travel.mp4',
        'preview.png', 'contact-sheet.jpg', 'trajectory.csv', 'diagnostics.json', 'model.json')]


def build(output):
    output = Path(output).resolve()
    if output == ROOT or ROOT.is_relative_to(output) or output.is_relative_to(ROOT / 'reconstruction'):
        raise ValueError('Choose a separate staging directory')
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError('Staging directory must be empty')
    for name in ASSETS:
        source = ROOT / 'reconstruction' / name
        target = output / 'reconstruction' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix == '.html':
            def link(match):
                relative = match[1]
                path = (source.parent / relative).resolve().relative_to(ROOT)
                if not (ROOT / path).is_file():
                    raise ValueError('Missing documentation: ' + relative)
                return 'href="https://github.com/ddanila/koshechka/blob/main/' + path.as_posix() + '"'
            target.write_text(re.sub(r'href="([^":]+\.md)"', link, source.read_text()))
        else:
            shutil.copyfile(source, target)
    (output / 'index.html').write_text('<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=reconstruction/index.html"><a href="reconstruction/index.html">Open Koshechka</a>')
    (output / '.nojekyll').touch()
    for page in output.rglob('*.html'):
        for url in re.findall(r'(?:href|src)="([^"]+)"', page.read_text()):
            if ':' not in url and not url.startswith('#') and not (page.parent / url.split('#')[0]).is_file():
                raise ValueError('Broken local link: ' + url)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    build(parser.parse_args().output)
