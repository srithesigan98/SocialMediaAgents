# Senang Homes logo pack

Clean vector reconstruction of the house outline and spaced serif wordmark used in the SenangHomes Bangsar carousel and Lantern thumbnail. The earlier generated images varied slightly; this pack establishes one consistent reusable version.

## Start here

- Light backgrounds: `svg/horizontal-primary.svg` or `png/horizontal-primary@2x.png`.
- Dark backgrounds: `svg/horizontal-reverse.svg` or `png/horizontal-reverse@2x.png`.
- Instagram profile: `png/profile-forest@1x.png` (1080 × 1080).
- Small avatar: `png/profile-icon@1x.png`.
- Symbol alone: `svg/icon-gold.svg`.
- See `previews/logo-collection.png` for an overview.

## Included

26 SVG files and 54 PNG files:

- Horizontal logo, stacked logo and wordmark in primary, reverse, forest, gold, black and white.
- House icon in forest, gold, black and white.
- Three square social profile graphics, with solid backgrounds suitable for circular cropping.
- SVG favicon and PNG icons at 32, 64, 180 and 512 pixels.
- PNGs for all other designs at native size (@1x) and double size (@2x).

All logo PNGs have transparent backgrounds, except the three profile graphics, whose backgrounds are intentional. White and reverse transparent logos should be viewed on dark backgrounds.

## Vector construction

All lettering is converted to paths; SVGs require no installed fonts, contain no linked assets and contain no embedded raster images. The wordmark is based on Georgia Regular with added tracking. The house symbol is a continuous angular outline. The files are editable vector artwork and scale without losing quality.

## Brand colours

- Forest green: #183E35
- Antique gold: #B28B53
- Warm cream: #F5F1E7
- Black: #000000
- White: #FFFFFF

Keep a clear area around the logo at least equal to the height of a wordmark capital letter. Retain the supplied proportions; do not stretch, add shadows or redraw the icon. Use the icon alone when the full wordmark would become too small to read.

Use the primary logo on cream or white and the reverse logo on forest green. Use monochrome assets for one-colour printing or simple overlays.

## Production sources

`build-logos.ps1` rebuilds the SVGs using the Windows Georgia font and System.Drawing. `export.cjs` exports PNGs using Sharp from the bundled runtime and builds the overview. These scripts are not required to use the finished files.
