"""Shared image generation entry point for image requests and video jobs."""
from fabricapp.ai.main import generate_tryon_image


def generate_image(data, *, generate=None):
    generate = generate or generate_tryon_image
    keys = ('person_image', 'fabric_image', 'garment_image', 'garment_type',
            'garment_style', 'gender', 'body_type', 'face_choice', 'face_image',
            'camera_view', 'background', 'additional_style_note', 'pose', 'seed', 'guidance')
    kwargs = {key: data.get(key) for key in keys}
    kwargs.update(fabric_type=data.get('fabric_type', 'unspecified'),
                  garment_details=data.get('garment_details', []), options=data.get('options', {}))
    return generate(**kwargs)
