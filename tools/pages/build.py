"""Regenerate the image tool pages, the three image guides and the /decide and
/chaos endpoint pages in web/.

Run from anywhere: python tools/pages/build.py
Then check that git status shows only the pages you meant to change, and copy
the changed files to the root of the website branch with the same commit
message, as web/README.md describes.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'web')
DATA = os.path.join(HERE, 'data')

RUNS = [
    ['make_image_pages.py', WEB, os.path.join(DATA, 'results-images.json'), os.path.join(DATA, 'results-more.json'),
     os.path.join(DATA, 'results-heic.json'), os.path.join(DATA, 'results-resize.json')],
    ['make_post_photo_location.py', WEB, os.path.join(DATA, 'results-more.json')],
    ['make_post_favicon.py', WEB, os.path.join(DATA, 'results-more.json')],
    ['make_post_convert.py', WEB, DATA],
    ['make_logic_pages.py', WEB, os.path.join(DATA, 'decide-examples.json')],
]

for script, *args in RUNS:
    subprocess.run([sys.executable, os.path.join(HERE, script)] + args, check=True)

# Last, so every page, these included, carries the current header and stylesheet link.
subprocess.run([sys.executable, os.path.join(os.path.dirname(HERE), 'site_nav.py')], check=True)
