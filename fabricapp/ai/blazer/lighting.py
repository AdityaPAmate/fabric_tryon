"""Blazer scene and illumination instructions for every generation route."""

from ..backgrounds import BACKGROUND_DESCRIPTIONS


CATALOG_LIGHTING = (
    "LIGHTING: use a colour-neutral studio key and fill on the person, with "
    "balanced exposure and neutral white balance. Match the jacket's diffuse "
    "midtone colours to fabric image 1 under this neutral illumination. "
    "Retain the original fabric hue, saturation and midtone lightness, with "
    "natural fold shadows and highlights. Illuminate the person independently "
    "of the background atmosphere, without a colour cast on the jacket. "
)


def scene_and_lighting(scenario, background=None, pose=None):
    description = BACKGROUND_DESCRIPTIONS.get(background)
    if description:
        scene = "BACKGROUND: replace the whole area behind the person with this scene: " + description + ". "
        if pose == "cross_leg_chair_recline":
            scene += "Include an upholstered armchair for the seated pose. "
    elif scenario in ("person_photo", "person_pose"):
        source = "0" if scenario == "person_photo" else "2"
        scene = "BACKGROUND: preserve the setting from image " + source + ". "
    else:
        scene = "BACKGROUND: a plain neutral studio. "
    return scene + CATALOG_LIGHTING
