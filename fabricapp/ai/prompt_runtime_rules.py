"""Compatibility prompt transformations used by the scenario composer.

These exact phrases were formerly stored with generic pose data. They are
runtime composition rules rather than pose definitions.
"""

POSE_PHRASE_REPLACEMENTS = [
    ("hands, arms, background, and body pose from image 0 completely unchanged",
     "and background from image 0 completely unchanged"),
    ("hands, arms, body pose, and the entire background",
     "and the entire background"),
    ("the same pose and background",
     "the requested new pose and the same background"),
    ("the exact same pose, shirt, and background",
     "the requested new pose, the same shirt, and the same background"),
    ("footwear, face, pose, or background",
     "footwear, face, or background"),
    ("not the face, not the pose, not the background",
     "not the face, not the background"),
    ("given the person's current arm position in image 0",
     "given the person's arm position in the new pose"),
    ("body and pose in image 0",
     "body and the new pose"),
]
