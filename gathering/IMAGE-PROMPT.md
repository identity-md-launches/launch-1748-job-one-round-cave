# Gathering 21 image prompt

Installed mcp__image__generate_image, built-in mode via the imagegen skill.
Requested one square image; actual generated dimensions were 1254 × 1254.
Only pigment was extracted and added to the inherited wall.

Exact prompt:

> A simple isolated prehistoric pigment motif on a plain light beige background for adding to an existing cave painting. Centered motif: four small uneven red ochre and yellow ochre pebbles sitting side by side within a shallow charcoal U-shaped bowl, with a single chalk-white pebble immediately above the center, connected to the bowl by one short charcoal line. The entire motif is in the center of the square, approximately within x=200..824 and y=300..724. Hand made burnt-stick charcoal, rough dry worn earth pigment, speckled gaps. Only red ochre, yellow ochre, charcoal black, chalk white. No text, no letters, no numbers, no signatures, no frames, no logos, no hands, no frogs, no people. Flat primitive cave painting strokes, not a photo or 3D render. Plain uniform pale beige outside the isolated motif.

The beige background is discarded. finish_wall_21.py blends only earth
pigment onto unused stone, preserving all surrounding pixels. The main Pepe
and ancestors' marks remain those of the inherited wall.
