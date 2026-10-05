# Page generators

The eight image tool pages, the three image guides, the `/decide` and `/mock_response`
endpoint pages and the eight encoding endpoint pages in `web/` are generated.
Change the generator or its data here, not the HTML, or the next build undoes
the change.

| Script | Writes in `web/` |
|--------|------------------|
| `make_image_pages.py` | `free-image-converter-api.html`, `free-heic-to-jpg-converter.html`, `free-image-resizer-api.html`, `free-image-compression-api.html`, `free-image-metadata-viewer-api.html`, `free-exif-remover-api.html`, `free-image-color-palette-api.html`, `free-favicon-generator-api.html` |
| `make_post_photo_location.py` | `remove-gps-location-and-exif-data-from-photos.html`, plus its card in `ai-sense-posts.html` and its line in `sitemap.xml` |
| `make_post_favicon.py` | `favicon-sizes-and-the-files-a-website-needs.html`, plus its card and sitemap line |
| `make_post_convert.py` | `convert-heic-webp-png-and-jpg-images.html`, plus its card and sitemap line; the sizes in it come from `data/` |
| `make_logic_pages.py` | `free-public-api-decide-api-endpoint.html` and `free-public-api-mock-response-api-endpoint.html` |
| `make_codec_pages.py` | the eight pages for `hex_encode`, `hex_decode`, `base64url_encode`, `base64url_decode`, `url_encode`, `url_decode`, `html_encode` and `html_decode`; the examples were worked out with the service's own `libs/func_codec.php` |
| `make_markdown_pages.py` | the two pages for `html_to_markdown` and `markdown_to_html`; the examples were worked out with the service's own `libs/func_markdown.php` |

Run all seven with Python 3 and nothing but the standard library:

```sh
python tools/pages/build.py
```

A build with nothing changed leaves `git status` clean. That is the check that
the generators and the published pages still agree. The three posts add their
card and sitemap line only when the page is not listed yet, so a card that
needs new text is edited in `ai-sense-posts.html` itself.

The site header in every page, and the version on its stylesheet link, is
written by `../site_nav.py`. `build.py` runs it last, so a build leaves every
page with the current header.

The tool pages take the site header and footer from
`web/free-json-to-csv-api.html`, the posts from
`web/a-name-that-answers-for-24-hours.html`, and the two endpoint pages from
`web/free-public-api-dns-name-api-endpoint.html`. A change there reaches these
pages at the next build.

`data/` holds the example answers the pages show. They were recorded on
29 September 2026 by running each request through the service's own handler,
with ImageMagick, on test images: among them a photo with made-up EXIF and a
GPS position at the Oslo Opera House, and a logo of 600 x 200 pixels. The
stored JPEG and ZIP were left out, since the pages read only the stored JSON of
`image_metadata` and `image_colors`. The Storage links in the answers expired
24 hours after the recording.
`results-resize.json` was recorded the same way on 30 September, with the
same test photo of 1600 x 1200 pixels.

`data/decide-examples.json` holds the `/decide` examples and the answers the
Python reference in the service's own repository gives for them. The service
is tested against the same reference, so the pages show what it answers.

To publish, commit the changed files in `web/` on `main`, then copy them to the
root of the `website` branch and commit there with the same message, as
[`web/README.md`](../../web/README.md) describes.
