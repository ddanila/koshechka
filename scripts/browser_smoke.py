"""Exercise the local viewer and project-subpath Pages build in Chromium."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
from playwright.sync_api import sync_playwright
from build_site import build, ROOT


def exercise(page, url):
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(url)
    page.wait_for_function("document.querySelector('#clock').textContent !== '0.00 s'")
    page.click('#play')
    assert not page.locator('#analysis').evaluate('(e)=>e.open')
    page.locator('#analysis summary').click()
    page.wait_for_function("document.querySelector('#branches').textContent.includes('rad')")
    for time in (0, 1, 8, 16):
        page.locator('#time').evaluate('(e,t)=>{e.value=t;e.dispatchEvent(new Event("input"));}', time)
        page.wait_for_function('(t)=>document.querySelector("#clock").textContent === t.toFixed(2)+" s"', arg=time)
        assert ('Initial conditions' in page.locator('#branches').inner_text()) == (time == 0)
    image = page.locator('#motion').evaluate('(e)=>e.toDataURL()')
    page.locator('#angle').fill('45')
    page.locator('#follow').uncheck()
    page.wait_for_timeout(100)
    assert image == page.locator('#motion').evaluate('(e)=>e.toDataURL()')
    renders = set()
    for mode in ('paper', 'ink', 'wire', 'silhouette'):
        page.select_option('#mode', mode)
        page.wait_for_timeout(100)
        renders.add(page.locator('#screen').evaluate('(e)=>e.toDataURL()'))
    assert len(renders) == 4
    page.select_option('#rate', '2')
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.evaluate('window.KITTY.frames.forEach(f=>delete f.analysis); window.KittyAnalysis.draw(0)')
    assert 'older export' in page.locator('#analysis-note').inner_text()
    assert not errors, errors
    page.close()


with tempfile.TemporaryDirectory() as temp:
    build(Path(temp)/'koshechka')
    server = ThreadingHTTPServer(('127.0.0.1',0), partial(SimpleHTTPRequestHandler,directory=temp))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            exercise(browser.new_page(), (ROOT/'reconstruction/index.html').as_uri())
            exercise(browser.new_page(), f'http://127.0.0.1:{server.server_port}/koshechka/')
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
print('Browser checks passed: file, project subpath, controls, diagnostics, mobile and older data.')
