"""The browser build's wiring for the 3D view (.github/workflows/browser.yml).

Read as text, in the order the steps run: pygbag builds with graphik's page
template, Strata's grid relay is put next to the page, and only then is the
page checked and deployed.
"""

import os
import re

from preponderous.graphik.grid3d import web as grid3dweb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW = open(os.path.join(ROOT, ".github", "workflows", "browser.yml")).read()
REQUIREMENTS = open(os.path.join(ROOT, "requirements.txt")).read()


def stepIndex(text):
    index = WORKFLOW.find(text)
    assert index >= 0, text
    return index


def test_pygbag_builds_with_graphiks_template():
    build = WORKFLOW[stepIndex("name: Build with pygbag") :]
    build = build[: build.find("- name:", 1)]
    assert "templatePath()" in build
    assert '--template "$TEMPLATE"' in build
    assert "python -m pygbag --build --title Ophidian" in build


def test_the_relay_is_fetched_from_a_pinned_strata_release_next_to_the_page():
    assert re.search(r'STRATA_RELAY_VERSION: "0\.9\.0"', WORKFLOW)
    assert (
        "python -m preponderous.graphik.grid3d.relay --strata "
        "${{ env.STRATA_RELAY_VERSION }} --dest src/build/web"
    ) in WORKFLOW


def test_the_relay_comes_after_the_build_and_before_the_deploy():
    graphik = stepIndex("name: Put graphik into src")
    build = stepIndex("name: Build with pygbag")
    relay = stepIndex("name: Put Strata's grid relay next to the page")
    deploy = stepIndex("name: Deploy to arcade")
    assert graphik < build < relay < deploy


def test_the_build_checks_the_page_has_the_3d_toggle_and_the_relay():
    assert "test -f src/build/web/grid-relay.js" in WORKFLOW
    assert "grep -q 'id=\"graphik3d\"' src/build/web/index.html" in WORKFLOW


def test_the_pinned_graphik_has_the_browser_3d_view():
    # grid3d.web (the relay view, the template and the relay fetcher) came
    # with graphik 0.5.0; 0.5.1's template starts in 3D (remembering a
    # player's 2D), fetches the relay's scripts only when 3D is wanted, keeps
    # the page from scrolling (so a phone can't push the 2D/3D button off
    # screen) and says where the button is (buttonArea); 0.5.2 frames the
    # board for a phone held upright and has the on-screen keys (TouchKeys,
    # touchScreen) a touch screen needs for the keyboard's actions
    version = re.search(
        r"graphik/archive/refs/tags/v(\d+)\.(\d+)\.(\d+)\.zip", REQUIREMENTS
    )
    assert version and tuple(map(int, version.groups())) >= (0, 5, 2)


def test_graphiks_template_keeps_the_page_still_and_the_relay_for_later():
    template = open(grid3dweb.templatePath()).read()
    assert "html, body { overflow: hidden; }" in template
    # fetched by the page only when 3D is wanted, so ?view=2d fetches none
    assert '<script src="grid-relay.js"' not in template
    assert callable(grid3dweb.buttonArea)


def test_the_browser_build_starts_in_3d_as_the_desktop_does():
    # browser.yml builds with templatePath() as it is: 3D first
    assert "import templatePath; print(templatePath())" in WORKFLOW
    assert 'data-default-view="3d"' in open(grid3dweb.templatePath()).read()


def test_graphiks_template_carries_the_toggle_and_the_relay_canvas():
    template = open(grid3dweb.templatePath()).read()
    assert 'id="graphik3d"' in template
    assert 'id="relay"' in template
    assert "grid-relay.js" in template
