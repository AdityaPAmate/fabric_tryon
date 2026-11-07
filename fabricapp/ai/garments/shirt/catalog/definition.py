"""Shirt catalog adapter. The runner contains no shirt-specific decisions."""
from fabricapp.catalog_engine.contracts import CatalogDefinition, Shot
from fabricapp.ai.garments.shirt.catalog.layout import get_layout, OUTPUT_SIZES
from fabricapp.ai.garments.shirt.catalog.prompts import edit_config
from fabricapp.ai.references.catalog_reference import CATALOG_REFERENCE_DIR


def build_config(data, shot, seed):
    return edit_config(data, shot.description, seed, reference_template=shot.reference, view=shot.key)


def _pipeline_options(view):
    framing = (
        ' CATALOG FRONT CAMERA: one narrow full-length portrait. Keep the complete person '
        'from the top of the hair to both shoes inside the frame, with small margins above '
        'and below. The person fills almost the entire image height. Keep the shoulders '
        'and arms fully inside the narrow frame, with only thin background margins on '
        'both sides. Preserve natural body proportions; do not shrink or stretch the person. '
        if view == 'front' else
        ' CATALOG CLOSE-UP CAMERA: fill this portrait panel from the top of the hair '
        'to just below the shirt hem. Keep small top and bottom margins and little '
        'background beside the shoulders. Preserve the complete shirt, head and '
        'natural body proportions. The frame ends at the hips, not at the knees or shoes. '
    )
    return {'_catalog_config': {'output_dimensions': OUTPUT_SIZES[view], 'framing': framing,
                                'version_suffix': '-catalog-panel-v2'}}


SHOTS = (
    Shot('front', 'front full-body view', 'pipeline', 'full_body', camera_view='front',
         pipeline_options=_pipeline_options('front')),
    Shot('close_up', 'standard camera close-up', 'pipeline', 'head_to_hip', camera_view='close_up',
         pipeline_options=_pipeline_options('close_up')),
    Shot('back', 'REAR CLOSE-UP product photograph, facing directly away from the camera. Fill the frame with the entire back of the head with a little space above the hair, shoulders, and the full shirt down to its lower hem. Keep the face turned away. Do not frame a complete head-to-feet person',
         'anchor_edit', 'rear_close_up', ('front',), scenario='person_pose'),
    *(Shot(key, description, 'template_edit', 'template_close_up',
           reference=CATALOG_REFERENCE_DIR / 'shirt' / filename)
      for key, filename, description in (
          ('collar', 'shirt_collar.png', 'extreme close-up of the shirt collar, collar points and top two buttons; frame from below the chin to the upper chest only; exclude the face, eyes, hair, waist and arms'),
          ('cuff', 'sleeve.png', 'extreme close-up of one existing shirt sleeve cuff and its seam, with only a small adjoining area of sleeve and arm; exclude face and full torso'),
          ('hem', 'hem.png', 'extreme close-up of the lower shirt hem, curved edge and hem stitching, with only a small adjoining section of shirt fabric and trousers; exclude face and chest'))),
)
DEFINITION = CatalogDefinition('shirt', 'classic-v1', SHOTS, build_config, get_layout)
