"""Blazer output composition rules, independent of fabric and garment styling."""


def composition_rule(scenario, camera):
    if scenario == "person_photo":
        return ""
    if camera == "close_up":
        return (
            "COMPOSITION: use the requested head-to-hip close-up. Recreate the "
            "selected upper-body pose within this crop. "
        )
    rule = (
        "COMPOSITION: complete head-to-feet photograph. Keep the entire head, "
        "both hands, full trouser legs and both shoes inside the frame, with "
        "space above the head and ground below the shoes. Position the camera "
        "far enough away to include the complete pose; retain natural body proportions. "
    )
    if scenario in ("person_pose", "face_photo"):
        rule += (
            "Image 2 is an identity reference, not an output composition template. "
            "Reconstruct the complete body even when the reference is cropped. "
        )
    if scenario == "person_pose":
        rule += (
            "Replace the posture in image 2 with the selected pose: follow its "
            "hand placement, arm bends, leg placement and head direction. "
        )
    return rule
